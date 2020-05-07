import os
import tempfile
import zipfile
import logging
import datetime as dt
import geojson
import ee
import shapefile
from django.http import JsonResponse, HttpResponseNotAllowed, HttpResponseRedirect
from django.shortcuts import render
from simplejson.errors import JSONDecodeError
from tethys_sdk.gizmos import SelectInput, DatePicker, Button, MapView, MVView, PlotlyView, MVDraw
from tethys_sdk.permissions import login_required
from tethys_sdk.workspaces import user_workspace
from ..helpers import generate_figure, find_shapefile, write_boundary_shapefile, prep_boundary_dir, \
    compute_dates_for_product
from ..gee.methods import get_image_collection_asset, get_time_series_from_image_collection, upload_shapefile_to_gee, \
    get_boundary_fc_props_for_user
from ..gee.products import EE_PRODUCTS

log = logging.getLogger(f'tethys.apps.{__name__}')


@login_required()
@user_workspace
def viewer(request, user_workspace):
    """
    Controller for the app viewer page.
    """
    default_platform = 'modis'
    default_sensors = EE_PRODUCTS[default_platform]
    first_sensor_key = next(iter(default_sensors.keys()))
    default_products = default_sensors[first_sensor_key]
    first_product_key = next(iter(default_products.keys()))
    first_product = default_products[first_product_key]

    # Build initial platform control
    platform_select = SelectInput(
        name='platform',
        display_text='Satellite Platform',
        options=(
            ('MODIS', 'modis'),
            ('Sentinel', 'sentinel'),
            ('Landsat', 'landsat')
        )
    )

    # Build initial sensor control
    sensor_options = []

    for sensor in default_sensors:
        sensor_options.append((sensor.upper(), sensor))

    sensor_select = SelectInput(
        name='sensor',
        display_text='Sensor',
        options=sensor_options
    )

    # Build initial product control
    product_options = []
    for product, info in default_products.items():
        product_options.append((info['display'], product))

    product_select = SelectInput(
        name='product',
        display_text='Product',
        options=product_options
    )

    # Get initial default dates and date ranges for date picker controls
    first_product_dates = compute_dates_for_product(first_product)

    start_date = DatePicker(
        name='start_date',
        display_text='Start Date',
        format='yyyy-mm-dd',
        start_view='decade',
        today_button=True,
        today_highlight=True,
        start_date=first_product_dates['beg_valid_date_range'],
        end_date=first_product_dates['end_valid_date_range'],
        initial=first_product_dates['default_start_date'],
        autoclose=True
    )

    end_date = DatePicker(
        name='end_date',
        display_text='End Date',
        format='yyyy-mm-dd',
        start_view='decade',
        today_button=True,
        today_highlight=True,
        start_date=first_product_dates['beg_valid_date_range'],
        end_date=first_product_dates['end_valid_date_range'],
        initial=first_product_dates['default_end_date'],
        autoclose=True
    )

    # Build reducer method control
    reducer_select = SelectInput(
        name='reducer',
        display_text='Reduction Method',
        options=(
            ('Median', 'median'),
            ('Mosaic', 'mosaic'),
            ('Mode', 'mode'),
            ('Mean', 'mean'),
            ('Minimum', 'min'),
            ('Maximum', 'max'),
            ('Sum', 'sum'),
            ('Count', 'count'),
            ('Product', 'product'),
        )
    )

    # Build Buttons
    load_button = Button(
        name='load_map',
        display_text='Load',
        style='default',
        attributes={'id': 'load_map'}
    )

    clear_button = Button(
        name='clear_map',
        display_text='Clear',
        style='default',
        attributes={'id': 'clear_map'}
    )

    plot_button = Button(
        name='load_plot',
        display_text='Plot AOI',
        style='default',
        attributes={'id': 'load_plot'}
    )

    # Get bounding box from user boundary if it exists
    boundary_props = get_boundary_fc_props_for_user(request.user)

    map_view = MapView(
        height='100%',
        width='100%',
        controls=[
            'ZoomSlider', 'Rotate', 'FullScreen',
            {'ZoomToExtent': {
                'projection': 'EPSG:4326',
                'extent': boundary_props.get('bbox', [-180, -90, 180, 90])  # Default to World
            }}
        ],
        basemap=[
            'CartoDB',
            {'CartoDB': {'style': 'dark'}},
            'OpenStreetMap',
            'Stamen',
            'ESRI'
        ],
        view=MVView(
            projection='EPSG:4326',
            center=boundary_props.get('centroid', [0, 0]),  # Default to World
            zoom=boundary_props.get('zoom', 3),  # Default to World
            maxZoom=18,
            minZoom=2
        ),
        draw=MVDraw(
            controls=['Pan', 'Modify', 'Delete', 'Move', 'Point', 'Polygon', 'Box'],
            initial='Pan',
            output_format='GeoJSON'
        )
    )

    # Boundary Upload Form
    set_boundary_button = Button(
        name='set_boundary',
        display_text='Set Boundary',
        style='default',
        attributes={
            'id': 'set_boundary',
            'data-toggle': 'modal',
            'data-target': '#set-boundary-modal'  # ID of the Set Boundary Modal
        }
    )

    # Handle Set Boundary Form
    set_boundary_error = ''
    if request.POST and request.FILES:
        set_boundary_error = handle_shapefile_upload(request, user_workspace)

        if not set_boundary_error:
            # Redirect back to this page to clear form
            return HttpResponseRedirect(request.path)

    context = {
        'platform_select': platform_select,
        'sensor_select': sensor_select,
        'product_select': product_select,
        'start_date': start_date,
        'end_date': end_date,
        'reducer_select': reducer_select,
        'load_button': load_button,
        'clear_button': clear_button,
        'plot_button': plot_button,
        'set_boundary_button': set_boundary_button,
        'set_boundary_error': set_boundary_error,
        'ee_products': EE_PRODUCTS,
        'map_view': map_view
    }

    return render(request, 'earth_engine/viewer.html', context)


@login_required()
def get_image_collection(request):
    """
    Controller to handle image collection requests.
    """
    response_data = {'success': False}

    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    try:
        log.debug(f'POST: {request.POST}')

        platform = request.POST.get('platform', None)
        sensor = request.POST.get('sensor', None)
        product = request.POST.get('product', None)
        start_date = request.POST.get('start_date', None)
        end_date = request.POST.get('end_date', None)
        reducer = request.POST.get('reducer', None)

        url = get_image_collection_asset(
            request=request,
            platform=platform,
            sensor=sensor,
            product=product,
            date_from=start_date,
            date_to=end_date,
            reducer=reducer
        )

        log.debug(f'Image Collection URL: {url}')

        response_data.update({
            'success': True,
            'url': url
        })

    except Exception as e:
        response_data['error'] = f'Error Processing Request: {e}'

    return JsonResponse(response_data)


@login_required()
def get_time_series_plot(request):
    context = {'success': False}

    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    try:
        log.debug(f'POST: {request.POST}')

        platform = request.POST.get('platform', None)
        sensor = request.POST.get('sensor', None)
        product = request.POST.get('product', None)
        start_date = request.POST.get('start_date', None)
        end_date = request.POST.get('end_date', None)
        reducer = request.POST.get('reducer', None)
        index_name = request.POST.get('index_name', None)
        scale = float(request.POST.get('scale', 250))
        geometry_str = request.POST.get('geometry', None)

        # Derived parameters
        ee_product = EE_PRODUCTS[platform][sensor][product]
        display_name = ee_product['display']

        if not index_name:
            index_name = ee_product['index']

        try:
            geometry = geojson.loads(geometry_str)
        except JSONDecodeError:
            raise ValueError('Please draw an area of interest.')

        if index_name is None:
            raise ValueError(f"We're sorry, but plotting {display_name} is not supported at this time. Please select "
                             f"a different product.")

        time_series = get_time_series_from_image_collection(
            platform=platform,
            sensor=sensor,
            product=product,
            index_name=index_name,
            scale=scale,
            geometry=geometry,
            date_from=start_date,
            date_to=end_date,
            reducer=reducer
        )

        log.debug(f'Time Series: {time_series}')

        figure = generate_figure(
            figure_title=display_name,
            time_series=time_series
        )

        plot_view = PlotlyView(figure, height='200px', width='100%')

        context.update({
            'success': True,
            'plot_view': plot_view
        })

    except ValueError as e:
        context['error'] = str(e)

    except Exception:
        context['error'] = f'An unexpected error has occurred. Please try again.'
        log.exception('An unexpected error occurred.')

    return render(request, 'earth_engine/plot.html', context)


def handle_shapefile_upload(request, user_workspace):
    """
    Uploads shapefile to Google Earth Engine as an Asset.

    Args:
        request (django.Request): the request object.
        user_workspace (tethys_sdk.workspaces.Workspace): the User workspace object.

    Returns:
        str: Error string if errors occurred.
    """
    # Write file to temp for processing
    uploaded_file = request.FILES['boundary-file']

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_zip_path = os.path.join(temp_dir, 'boundary.zip')

        # Use with statements to ensure opened files are closed when done
        with open(temp_zip_path, 'wb') as temp_zip:
            for chunk in uploaded_file.chunks():
                temp_zip.write(chunk)

        try:
            # Extract the archive to the temporary directory
            with zipfile.ZipFile(temp_zip_path) as temp_zip:
                temp_zip.extractall(temp_dir)

        except zipfile.BadZipFile:
            # Return error message
            return 'You must provide a zip archive containing a shapefile.'

        # Verify that it contains a shapefile
        try:
            # Find a shapefile in directory where we extracted the archive
            shapefile_path = find_shapefile(temp_dir)

            if not shapefile_path:
                return 'No Shapefile found in the archive provided.'

            with shapefile.Reader(shapefile_path) as shp_file:
                # Check type (only Polygon supported)
                if shp_file.shapeType != shapefile.POLYGON:
                    return 'Only shapefiles containing Polygons are supported.'

                # Setup workspace directory for storing shapefile
                workspace_dir = prep_boundary_dir(user_workspace.path)

                # Write the shapefile to the workspace directory
                write_boundary_shapefile(shp_file, workspace_dir)

                # Upload shapefile as Asset in GEE
                upload_shapefile_to_gee(request.user, shp_file)

        except TypeError:
            return 'Incomplete or corrupted shapefile provided.'

        except ee.EEException:
            msg = 'An unexpected error occurred while uploading the shapefile to Google Earth Engine.'
            log.exception(msg)
            return msg
