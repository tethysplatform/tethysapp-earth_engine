import os
import tempfile
import zipfile
import glob
from pprint import pprint
import shapefile
import ee
import pandas as pd
from plotly import graph_objs as go


def generate_figure(figure_title, time_series):
    """
    Generate a figure from a list of time series Pandas DataFrames.

    Args:
        figure_title(str): Title of the figure.
        time_series(list<pandas.DataFrame>): list of time series Pandas DataFrames.
    """
    data = []
    yaxis_title = 'No Data'

    for index, df in enumerate(time_series):
        column_name = df.columns[1]
        yaxis_title = column_name
        series_name = f'{column_name} {index + 1}' if len(time_series) > 1 else column_name
        series_plot = go.Scatter(
            x=pd.to_datetime(df.iloc[:, 0], unit='ms'),
            y=df.iloc[:, 1],
            name=series_name,
            mode='lines'
        )

        data.append(series_plot)

    figure = {
        'data': data,
        'layout': {
            'title': {
                'text': figure_title,
                'pad': {
                    'b': 5,
                },
            },
            'yaxis': {'title': yaxis_title},
            'legend': {
                'orientation': 'h'
            },
            'margin': {
                'l': 40,
                'r': 10,
                't': 80,
                'b': 10
            }
        }
    }

    return figure


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
            return 'An unexpected error occurred while uploading the shapefile to Google Earth Engine.'


def find_shapefile(directory):
    """
    Recursively find the path to the first file with an extension ".shp" in the given directory.

    Args:
        directory (str): Path of directory to search for shapefile.

    Returns:
        str: Path to first shapefile found in given directory.
    """
    shapefile_path = ''

    # Scan the temp directory using walk, searching for a shapefile (.shp extension)
    for root, dirs, files in os.walk(directory):
        for f in files:
            f_path = os.path.join(root, f)
            f_ext = os.path.splitext(f_path)[1]

            if f_ext == '.shp':
                shapefile_path = f_path
                break

    return shapefile_path


def write_boundary_shapefile(shp_file, directory):
    """
    Write the shapefile to the given directory. The shapefile will be called "boundary.shp".

    Args:
        shp_file (shapefile.Reader): A shapefile reader object.
        directory (str): Path to directory to which to write shapefile.

    Returns:
        str: path to shapefile that was written.
    """
    # Name the shapefiles boundary.* (boundary.shp, boundary.dbf, boundary.shx)
    shapefile_path = os.path.join(directory, 'boundary')

    # Write contents of shapefile to new shapfile
    with shapefile.Writer(shapefile_path) as out_shp:
        # Based on https://pypi.org/project/pyshp/#examples
        out_shp.fields = shp_file.fields[1:]  # skip the deletion field

        # Add the existing shape objects
        for shaperec in shp_file.iterShapeRecords():
            out_shp.record(*shaperec.record)
            out_shp.shape(shaperec.shape)

    return shapefile_path


def prep_boundary_dir(root_path):
    """
    Setup the workspace directory that will store the uploaded boundary shapefile.

    Args:
        root_path (str): path to the root directory where the boundary directory will be located.

    Returns:
        str: path to boundary directory for storing boundary shapefile.
    """
    # Copy into new shapefile in user directory
    boundary_dir = os.path.join(root_path, 'boundary')

    # Make the directory if it doesn't exist
    if not os.path.isdir(boundary_dir):
        os.mkdir(boundary_dir)

    # Clear the directory if it exists
    else:
        # Find all files in the directory using glob
        files = glob.glob(os.path.join(boundary_dir, '*'))

        # Remove all the files
        for f in files:
            os.remove(f)

    return boundary_dir


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
        raise FileNotFoundError('No asset root directory could be found. '
                                'Please setup an asset root directory in the '
                                'Google Earth Engine account associated with '
                                'this app to use this feature.')

    asset_root_dir = asset_roots[0]['id']
    earth_engine_root_dir = os.path.join(asset_root_dir, 'earth_engine_app')
    user_root_dir = os.path.join(earth_engine_root_dir, user.username)

    # Create earth engine directory, will raise exception if it already exists
    try:
        ee.batch.data.createAsset({
            'type': 'Folder',
            'name': earth_engine_root_dir
        })
    except ee.EEException as e:
        if 'Cannot overwrite asset' not in str(e):
            raise e

    # Create user directory, will raise exception if it already exists
    try:
        ee.batch.data.createAsset({
            'type': 'Folder',
            'name': user_root_dir
        })
    except ee.EEException as e:
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
    except ee.EEException as e:
        # Nothing to delete, so pass
        if 'Asset not found' not in str(e):
            raise e

    # Export ee.Feature to ee.Asset
    task = ee.batch.Export.table.toAsset(
        collection=feature_collection,
        description='uploadToTableAsset',
        assetId=user_boundary_asset_path
    )

    task.start()
