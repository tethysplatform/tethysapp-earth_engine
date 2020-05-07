import os
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
