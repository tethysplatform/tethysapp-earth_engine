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
