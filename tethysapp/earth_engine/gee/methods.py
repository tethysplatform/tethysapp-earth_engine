import logging
import ee
from ee.ee_exception import EEException
from . import params as gee_account
from .products import EE_PRODUCTS
from . import cloud_mask as cm
import geojson
import pandas as pd

log = logging.getLogger(f'tethys.apps.{__name__}')

if gee_account.service_account:
    try:
        credentials = ee.ServiceAccountCredentials(gee_account.service_account, gee_account.private_key)
        ee.Initialize(credentials)
        log.info('Successfully initialized GEE using service account.')
    except EEException as e:
        log.warning('Unable to initialize GEE using service account. If installing ignore this warning.')
else:
    try:
        ee.Initialize()
    except EEException as e:
        log.warning('Unable to initialize GEE with local credentials. If installing ignore this warning.')


def image_to_map_id(image_name, vis_params={}):
    """
    Get map_id parameters
    """
    try:
        ee_image = ee.Image(image_name)
        map_id = ee_image.getMapId(vis_params)
        tile_url = map_id['tile_fetcher'].url_format
        return tile_url

    except EEException:
        log.exception('An error occurred while attempting to retrieve the map id.')

def get_image_collection_asset(platform, sensor, product, date_from=None, date_to=None, reducer='median'):
    """
    Get tile url for image collection asset.
    """
    ee_product = EE_PRODUCTS[platform][sensor][product]

    collection = ee_product['collection']
    index = ee_product.get('index', None)
    vis_params = ee_product.get('vis_params', {})
    cloud_mask = ee_product.get('cloud_mask', None)

    log.debug(f'Image Collection Name: {collection}')
    log.debug(f'Band Selector: {index}')
    log.debug(f'Vis Params: {vis_params}')

    try:
        ee_collection = ee.ImageCollection(collection)

        if date_from and date_to:
            ee_filter_date = ee.Filter.date(date_from, date_to)
            ee_collection = ee_collection.filter(ee_filter_date)

        if index:
            ee_collection = ee_collection.select(index)

        if cloud_mask:
            cloud_mask_func = getattr(cm, cloud_mask, None)
            if cloud_mask_func:
                ee_collection = ee_collection.map(cloud_mask_func)

        if reducer:
            ee_collection = getattr(ee_collection, reducer)()

        tile_url = image_to_map_id(ee_collection, vis_params)

        return tile_url

    except EEException:
        log.exception('An error occurred while attempting to retrieve the image collection asset.')

def get_time_series_from_image_collection(platform, sensor, product, index_name, scale=30, geometry=None,
                                      date_from=None, date_to=None, reducer='median'):
    """
    Derive time series at given geometry.
    """
    time_series = []
    ee_product = EE_PRODUCTS[platform][sensor][product]
    collection_name = ee_product['collection']

    if not isinstance(geometry, geojson.GeometryCollection):
        raise ValueError('Geometry must be a valid geojson.GeometryCollection')

    for geom in geometry.geometries:
        log.debug(f'Computing Time Series for Geometry of Type: {geom.type}')

        try:
            ee_geometry = None
            if isinstance(geom, geojson.Polygon):
                ee_geometry = ee.Geometry.Polygon(geom.coordinates)
            elif isinstance(geom, geojson.Point):
                ee_geometry = ee.Geometry.Point(geom.coordinates)
            else:
                raise ValueError('Only Points and Polygons are supported.')

            if date_from is not None:
                if index_name is not None:
                    indexCollection = ee.ImageCollection(collection_name) \
                        .filterDate(date_from, date_to) \
                        .select(index_name)
                else:
                    indexCollection = ee.ImageCollection(collection_name) \
                        .filterDate(date_from, date_to)
            else:
                indexCollection = ee.ImageCollection(collection_name)

            def get_index(image):
                if reducer:
                    the_reducer = getattr(ee.Reducer, reducer)()

                if index_name is not None:
                    index_value = image.reduceRegion(the_reducer, ee_geometry, scale).get(index_name)
                else:
                    index_value = image.reduceRegion(the_reducer, ee_geometry, scale)

                date = image.get('system:time_start')
                index_image = ee.Image().set('indexValue', [ee.Number(date), index_value])
                return index_image

            index_collection = indexCollection.map(get_index)
            index_collection_agg = index_collection.aggregate_array('indexValue')
            values = index_collection_agg.getInfo()
            log.debug('Values acquired.')
            df = pd.DataFrame(values, columns=['Time', index_name.replace("_", " ")])
            time_series.append(df)

        except EEException:
            log.exception('An error occurred while attempting to retrieve the time series.')

    log.debug(f'Time Series: {time_series}')
    return time_series