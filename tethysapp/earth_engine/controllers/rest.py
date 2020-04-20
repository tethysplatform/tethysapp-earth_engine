import logging
from django.http import JsonResponse
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view, authentication_classes

log = logging.getLogger(f'tethys.apps.{__name__}')


@api_view(['GET'])
@authentication_classes((TokenAuthentication,))
def get_time_series(request):
    """
    Controller for the app home page.
    """
    response_data = {
        'success': True,
        'status': 'Hello, World!'
    }
    return JsonResponse(response_data)
