from tethys_sdk.base import TethysAppBase


class EarthEngine(TethysAppBase):
    """
    Tethys app class for Earth Engine.
    """

    name = 'Google Earth Engine Tutorial'
    description = ''
    package = 'earth_engine'  # WARNING: Do not change this value
    index = 'home'
    icon = f'{package}/images/earth-engine-logo.png'
    root_url = 'earth-engine'
    color = '#524745'
    tags = ''
    enable_feedback = False
    feedback_emails = []