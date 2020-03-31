import os
import tempfile
import zipfile
import glob
import shapefile
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
    # Write file to temp for processing
    uploaded_file = request.FILES['boundary-file']

    with tempfile.TemporaryDirectory() as temp_dir:
        print(temp_dir)

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
                return 'No file with extension ".shp" found in archive provided.'

            with shapefile.Reader(shapefile_path) as shp_file:
                print(shp_file)

                # Check type (only Polygon supported)
                if shp_file.shapeType != shapefile.POLYGON:
                    return 'Only shapefiles containing Polygons are supported.'

                # Setup workspace directory for storing shapefile
                workspace_dir = setup_workspace_dir(user_workspace)

                # Write the shapefile to the workspace directory
                write_shapefile_to_workspace(shp_file, workspace_dir)

        except TypeError:
            return 'Incomplete or corrupted shapefile provided.'


def find_shapefile(temp_dir):
    """
    Recursively find the path to the first file with an extension ".shp" in the given directory.
    """
    shapefile_path = ''

    # Scan the temp directory usign walk, searching for a shapefile (.shp extension)
    for root, dirs, files in os.walk(temp_dir):
        for f in files:
            f_path = os.path.join(root, f)
            f_ext = os.path.splitext(f_path)[1]

            if f_ext == '.shp':
                shapefile_path = f_path
                break

    return shapefile_path


def write_shapefile_to_workspace(in_shp, workspace_dir):
    """
    Write the shapefile to the workspace directory.
    """
    # Name the shapefiles boundary.* (boundary.shp, boundary.dbf, boundary.shx)
    boundary_shp = os.path.join(workspace_dir, 'boundary')

    # Write contents of shapefile to new shapfile
    with shapefile.Writer(boundary_shp) as out_shp:
        # Based on https://pypi.org/project/pyshp/#examples
        out_shp.fields = in_shp.fields[1:]  # skip the deletion field

        # Add the existing shape objects
        for shaperec in in_shp.iterShapeRecords():
            out_shp.record(*shaperec.record)
            out_shp.shape(shaperec.shape)


def setup_workspace_dir(user_workspace):
    """
    Setup the workspace directory that will store the uploaded shapefiles.
    """
    # Copy into new shapefile in user directory
    boundary_dir = os.path.join(user_workspace.path, 'boundary')

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
