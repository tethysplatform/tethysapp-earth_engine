from tethys_sdk.base import TethysAppBase, url_map_maker


class EarthEngine(TethysAppBase):
    """
    Tethys app class for Earth Engine.
    """

    name = 'Earth Engine'
    index = 'earth_engine:home'
    icon = 'earth_engine/images/icon.gif'
    package = 'earth_engine'
    root_url = 'earth-engine'
    color = '#d35400'
    description = ''
    tags = ''
    enable_feedback = False
    feedback_emails = []

    def url_maps(self):
        """
        Add controllers
        """
        UrlMap = url_map_maker(self.root_url)

        url_maps = (
            UrlMap(
                name='home',
                url='earth-engine',
                controller='earth_engine.controllers.home'
            ),
        )

        return url_maps