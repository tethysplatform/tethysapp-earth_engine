from tethys_sdk.base import TethysAppBase, url_map_maker
from tethys_sdk.app_settings import CustomSetting


class EarthEngine(TethysAppBase):
    """
    Tethys app class for Earth Engine.
    """

    name = 'Earth Engine'
    index = 'earth_engine:home'
    icon = 'earth_engine/images/earth-engine-logo.png'
    package = 'earth_engine'
    root_url = 'earth-engine'
    color = '#524745'
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
                controller='earth_engine.controllers.home.home'
            ),
            UrlMap(
                name='about',
                url='earth-engine/about',
                controller='earth_engine.controllers.home.about'
            ),
            UrlMap(
                name='viewer',
                url='earth-engine/viewer',
                controller='earth_engine.controllers.viewer.viewer'
            ),
            UrlMap(
                name='get_image_collection',
                url='earth-engine/viewer/get-image-collection',
                controller='earth_engine.controllers.viewer.get_image_collection'
            ),
            UrlMap(
                name='get_time_series_plot',
                url='earth-engine/viewer/get-time-series-plot',
                controller='earth_engine.controllers.viewer.get_time_series_plot'
            ),
            UrlMap(
                name='rest_get_time_series',
                url='earth-engine/api/get-time-series',
                controller='earth_engine.controllers.rest.get_time_series'
            ),
        )

        return url_maps

    def custom_settings(self):
        """
        Custom settings.
        """
        custom_settings = (
            CustomSetting(
                name='service_account_email',
                type=CustomSetting.TYPE_STRING,
                description='Email associated with the service account.',
                default='',
                required=False,
            ),
            CustomSetting(
                name='private_key_file',
                type=CustomSetting.TYPE_STRING,
                description='Path to service account JSON file containing the private key.',
                default='',
                required=False,
            ),
        )
        return custom_settings

