from tethys_sdk.app_settings import CustomSetting
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
