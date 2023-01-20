import datetime as dt
import geojson
import logging
from simplejson.errors import JSONDecodeError

from django.http import JsonResponse, HttpResponseNotAllowed, HttpResponseRedirect
from django.shortcuts import render
from tethys_sdk.routing import controller
from tethys_sdk.gizmos import SelectInput, DatePicker, Button, MapView, MVView, PlotlyView, MVDraw

from ..helpers import generate_figure, handle_shapefile_upload, compute_dates_for_product
from ..gee.methods import get_image_collection_asset, get_time_series_from_image_collection, \
    get_boundary_fc_props_for_user
from ..gee.products import EE_PRODUCTS

log = logging.getLogger(f'tethys.apps.{__name__}')


@controller(user_workspace=True, url='viewer')
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
        style='outline-secondary',
        attributes={'id': 'load_map'}
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

    clear_button = Button(
        name='clear_map',
        display_text='Clear',
        style='outline-secondary',
        attributes={'id': 'clear_map'},
        classes='mt-2',
    )

    plot_button = Button(
        name='load_plot',
        display_text='Plot AOI',
        style='outline-secondary',
        attributes={'id': 'load_plot'},
    )

    # Boundary Upload Form
    set_boundary_button = Button(
        name='set_boundary',
        display_text='Set Boundary',
        style='outline-secondary',
        attributes={
            'id': 'set_boundary',
            'data-bs-toggle': 'modal',
            'data-bs-target': '#set-boundary-modal',  # ID of the Set Boundary Modal
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


@controller(url='viewer/get-image-collection')
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

@controller(url='viewer/get-time-series-plot')
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
