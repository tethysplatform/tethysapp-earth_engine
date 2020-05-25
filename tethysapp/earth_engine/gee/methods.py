import os
import math
import logging
import ee
from ee.ee_exception import EEException
import geojson
import pandas as pd
from . import cloud_mask as cm
from .products import EE_PRODUCTS
from ..app import EarthEngine as app


log = logging.getLogger(f'tethys.apps.{__name__}')

service_account = app.get_custom_setting('service_account_email')
private_key_path = app.get_custom_setting('private_key_file')

if service_account and private_key_path and os.path.isfile(private_key_path):
    try:
        credentials = ee.ServiceAccountCredentials(service_account, private_key_path)
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


def get_image_collection_asset(request, platform, sensor, product, date_from=None, date_to=None, reducer='median'):
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

        # Attempt to clip the image by the boundary provided by the user
        clip_features = get_boundary_fc_for_user(request.user)

        if clip_features:
            ee_collection = ee_collection.clipToCollection(clip_features)

        tile_url = image_to_map_id(ee_collection, vis_params)

        return tile_url

    except EEException:
        log.exception('An error occurred while attempting to retrieve the image collection asset.')


def get_time_series_from_image_collection(platform, sensor, product, index_name, scale=30, geometry=None,
                                          date_from=None, date_to=None, reducer='median', orient='df'):
    """
    Derive time series at given geometry.
    """
    time_series = []
    ee_product = EE_PRODUCTS[platform][sensor][product]
    collection_name = ee_product['collection']

    if not isinstance(geometry, geojson.GeometryCollection):
        raise ValueError('Geometry must be a valid GeoJSON GeometryCollection.')

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

            if orient == 'df':
                time_series.append(df)
            else:
                time_series.append(df.to_dict(orient=orient))

        except EEException:
            log.exception('An error occurred while attempting to retrieve the time series.')

    log.debug(f'Time Series: {time_series}')
    return time_series


def upload_shapefile_to_gee(user, shp_file):
    """
    Upload a shapefile to Google Earth Engine as an asset.

    Args:
        user (django.contrib.auth.User): the request user.
        shp_file (shapefile.Reader): A shapefile reader object.
    """
    features = []
    fields = shp_file.fields[1:]
    field_names = [field[0] for field in fields]

    # Convert Shapefile to ee.Features
    for record in shp_file.shapeRecords():
        # First convert to geojson
        attributes = dict(zip(field_names, record.record))
        geojson_geom = record.shape.__geo_interface__
        geojson_feature = {
            'type': 'Feature',
            'geometry': geojson_geom,
            'properties': attributes
        }

        # Create ee.Feature from geojson (this is the Upload, b/c ee.Feature is a server object)
        features.append(ee.Feature(geojson_feature))

    feature_collection = ee.FeatureCollection(features)

    # Get unique folder for each user to story boundary asset
    user_boundary_asset_path = get_user_boundary_path(user)

    # Overwrite an existing asset with this name by deleting it first
    try:
        ee.batch.data.deleteAsset(user_boundary_asset_path)
    except EEException as e:
        # Nothing to delete, so pass
        if 'Asset not found' not in str(e):
            log.exception('Encountered an unhandled EEException.')
            raise e

    # Export ee.Feature to ee.Asset
    task = ee.batch.Export.table.toAsset(
        collection=feature_collection,
        description='uploadToTableAsset',
        assetId=user_boundary_asset_path
    )

    task.start()


def get_asset_dir_for_user(user):
    """
    Get a unique asset directory for given user.

    Args:
        user (django.contrib.auth.User): the request user.

    Returns:
        str: asset directory path for given user.
    """
    asset_roots = ee.batch.data.getAssetRoots()

    if len(asset_roots) < 1:
        # Initialize the asset root directory if one doesn't exist already
        ee.batch.data.createAssetHome('users/earth_engine_app')

    asset_root_dir = asset_roots[0]['id']
    earth_engine_root_dir = os.path.join(asset_root_dir, 'earth_engine_app')
    user_root_dir = os.path.join(earth_engine_root_dir, user.username)

    # Create earth engine directory, will raise exception if it already exists
    try:
        ee.batch.data.createAsset({
            'type': 'Folder',
            'name': earth_engine_root_dir
        })
    except EEException as e:
        if 'Cannot overwrite asset' not in str(e):
            raise e

    # Create user directory, will raise exception if it already exists
    try:
        ee.batch.data.createAsset({
            'type': 'Folder',
            'name': user_root_dir
        })
    except EEException as e:
        if 'Cannot overwrite asset' not in str(e):
            raise e

    return user_root_dir


def get_user_boundary_path(user):
    """
    Get a unique path for the user boundary asset.

    Args:
        user (django.contrib.auth.User): the request user.

    Returns:
        str: the unique path for the user boundary asset.
    """
    user_asset_dir = get_asset_dir_for_user(user)
    user_boundary_asset_path = os.path.join(user_asset_dir, 'boundary')
    return user_boundary_asset_path


def get_boundary_fc_for_user(user):
    """
    Get the boundary FeatureClass for the given user if it exists.

    Args:
        user (django.contrib.auth.User): the request user.

    Returns:
        ee.FeatureCollection: boundary feature collection or None
    """
    try:
        boundary_path = get_user_boundary_path(user)
        # If no boundary exists for the user, an exception occur when calling this and clipping will skipped
        ee.batch.data.getAsset(boundary_path)
        # Add the clip option
        fc = ee.FeatureCollection(boundary_path)
        return fc
    except EEException:
        pass

    return None


def get_boundary_fc_props_for_user(user):
    """
    Get various properties of the boundary FeatureCollection.
    Args:
        user (django.contrib.auth.User): Get the properties of the boundary uploaded by this user.

    Returns:
        dict<zoom,bbox,centroid>: Dictionary containing the centroid and bounding box of the boundary and the approximate OpenLayers zoom level to frame the boundary around the centroid. Empty dictionary if no boundary FeatureCollection is found for the given user.
    """
    fc = get_boundary_fc_for_user(user)

    if not fc:
        return dict()

    # Compute bounding box
    bounding_rect = fc.geometry().bounds().getInfo()
    bounding_coords = bounding_rect.get('coordinates')[0]

    # Derive bounding box from two corners of the bounding rectangle
    bbox = [bounding_coords[0][0], bounding_coords[0][1], bounding_coords[2][0], bounding_coords[2][1]]

    # Get centroid
    centroid = fc.geometry().centroid().getInfo()

    # Compute length diagonal of bbox for zoom calculation
    diag = math.sqrt((bbox[0] - bbox[2])**2 + (bbox[1] - bbox[3])**2)

    # Found the diagonal length and zoom level for US and Kenya boundaries
    # Used equation of a line to develop the relationship between zoom and diagonal of bounding box
    zoom = round((-0.0701 * diag) + 8.34, 0)

    # The returned ee.FeatureClass properties
    fc_props = {
        'zoom': zoom,
        'bbox': bbox,
        'centroid': centroid.get('coordinates')
    }

    return fc_props
