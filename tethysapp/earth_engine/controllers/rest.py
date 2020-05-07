import logging
import datetime as dt
import geojson
from simplejson import JSONDecodeError
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseServerError
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view, authentication_classes
from ..gee.products import EE_PRODUCTS
from ..gee.methods import get_time_series_from_image_collection
from ..helpers import compute_dates_for_product

log = logging.getLogger(f'tethys.apps.{__name__}')


@api_view(['GET', 'POST'])
@authentication_classes((TokenAuthentication,))
def get_time_series(request):
    """
    Controller for the get-time-series REST endpoint.
    """
    # Get request parameters.
    if request.method == 'GET':
        data = request.GET.copy()
    elif request.method == 'POST':
        data = request.POST.copy()
    else:
        return HttpResponseBadRequest('Only GET and POST methods are supported.')

    platform = data.get('platform', None)
    sensor = data.get('sensor', None)
    product = data.get('product', None)
    start_date_str = data.get('start_date', None)
    end_date_str = data.get('end_date', None)
    reducer = data.get('reducer', 'median')
    index = data.get('index', None)
    scale_str = data.get('scale', 250)
    orient = data.get('orient', 'list')
    geometry_str = data.get('geometry', None)

    # validate given parameters
    # platform
    if not platform or platform not in EE_PRODUCTS:
        valid_platform_str = '", "'.join(EE_PRODUCTS.keys())
        return HttpResponseBadRequest(f'The "platform" parameter is required. Valid platforms '
                                      f'include: "{valid_platform_str}".')

    # sensors
    if not sensor or sensor not in EE_PRODUCTS[platform]:
        valid_sensor_str = '", "'.join(EE_PRODUCTS[platform].keys())
        return HttpResponseBadRequest(f'The "sensor" parameter is required. Valid sensors for the "{platform}" '
                                      f'platform include: "{valid_sensor_str}".')

    # product
    if not product or product not in EE_PRODUCTS[platform][sensor]:
        valid_product_str = '", "'.join(EE_PRODUCTS[platform][sensor].keys())
        return HttpResponseBadRequest(f'The "product" parameter is required. Valid products for the "{platform} '
                                      f'{sensor}" sensor include: "{valid_product_str}".')

    selected_product = EE_PRODUCTS[platform][sensor][product]

    # index
    # if index not provided, get default index from product properties
    if not index:
        index = selected_product['index']

    # if index is still None (not defined for the product) it is not supported currently
    if index is None:
        return HttpResponseBadRequest(
            f'Retrieving time series for "{platform} {sensor} {product}" is not supported at this time.'
        )

    # get valid dates for selected product
    product_dates = compute_dates_for_product(selected_product)

    # assign default start date if not provided
    if not start_date_str:
        start_date_str = product_dates['default_start_date']

    # assign default start date if not provided
    if not end_date_str:
        end_date_str = product_dates['default_end_date']

    # convert to datetime objects for validation
    try:
        start_date_dt = dt.datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date_dt = dt.datetime.strptime(end_date_str, '%Y-%m-%d')
    except ValueError:
        return HttpResponseBadRequest(
            'Invalid date format. Please use "YYYY-MM-DD".'
        )

    beg_valid_date_range = dt.datetime.strptime(product_dates['beg_valid_date_range'], '%Y-%m-%d')
    end_valid_date_range = dt.datetime.strptime(product_dates['end_valid_date_range'], '%Y-%m-%d')

    # start_date in valid range
    if start_date_dt < beg_valid_date_range or start_date_dt > end_valid_date_range:
        return HttpResponseBadRequest(
            f'The date {start_date_str} is not a valid "start_date" for "{platform} {sensor} {product}". '
            f'It must occur between {product_dates["beg_valid_date_range"]} '
            f'and {product_dates["end_valid_date_range"]}.'
        )

    # end_date in valid range
    if end_date_dt < beg_valid_date_range or end_date_dt > end_valid_date_range:
        return HttpResponseBadRequest(
            f'The date {end_date_str} is not a valid "end_date" for "{platform} {sensor} {product}". '
            f'It must occur between {product_dates["beg_valid_date_range"]} '
            f'and {product_dates["end_valid_date_range"]}.'
        )

    # start_date before end_date
    if start_date_dt > end_date_dt:
        return HttpResponseBadRequest(
            f'The "start_date" must occur before the "end_date". Dates given: '
            f'start_date = {start_date_str}; end_date = {end_date_str}.'
        )

    # reducer
    valid_reducers = ('median', 'mosaic', 'mode', 'mean', 'min', 'max', 'sum', 'count', 'product')
    if reducer not in valid_reducers:
        valid_reducer_str = '", "'.join(valid_reducers)
        return HttpResponseBadRequest(
            f'The value "{reducer}" is not valid for parameter "reducer". '
            f'Must be one of: "{valid_reducer_str}". Defaults to "median" '
            f'if not given.'
        )

    # orient
    valid_orient_vals = ('dict', 'list', 'series', 'split', 'records', 'index')
    if orient not in valid_orient_vals:
        valid_orient_str = '", "'.join(valid_orient_vals)
        return HttpResponseBadRequest(
            f'The value "{orient}" is not valid for parameter "orient". '
            f'Must be one of: "{valid_orient_str}". Defaults to "dict" '
            f'if not given.'
        )

    # scale
    try:
        scale = float(scale_str)
    except ValueError:
        return HttpResponseBadRequest(
            f'The "scale" parameter must be a valid number, but "{scale_str}" was given.'
        )

    # geometry
    bad_geometry_msg = 'The "geometry" parameter is required and must be a valid geojson string.'
    if not geometry_str:
        return HttpResponseBadRequest(bad_geometry_msg)

    try:
        geometry = geojson.loads(geometry_str)
    except JSONDecodeError:
        return HttpResponseBadRequest(bad_geometry_msg)

    try:
        time_series = get_time_series_from_image_collection(
            platform=platform,
            sensor=sensor,
            product=product,
            index_name=index,
            scale=scale,
            geometry=geometry,
            date_from=start_date_str,
            date_to=end_date_str,
            reducer=reducer,
            orient=orient
        )
    except ValueError as e:
        return HttpResponseBadRequest(str(e))
    except Exception:
        log.exception('An unexpected error occurred during execution of get_time_series_from_image_collection.')
        return HttpResponseServerError('An unexpected error occurred. Please review your parameters and try again.')

    # compose response object.
    response_data = {
        'time_series': time_series,
        'parameters': {
            'platform': platform,
            'sensor': sensor,
            'product': product,
            'index': index,
            'start_date': start_date_str,
            'end_date': end_date_str,
            'reducer': reducer,
            'orient': orient,
            'scale': scale,
            'geometry': geometry
        }
    }

    return JsonResponse(response_data)
