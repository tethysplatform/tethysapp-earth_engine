from tethys_sdk.base import TethysAppBase


class App(TethysAppBase):
    """
    Tethys app class for Earth Engine.
    """

    name = 'Earth Engine'
    description = ''
    package = 'earth_engine'  # WARNING: Do not change this value
    index = 'home'
    icon = f'{package}/images/icon.gif'
    root_url = 'earth-engine'
    color = '#273c75'
    tags = ''
    enable_feedback = False
    feedback_emails = []