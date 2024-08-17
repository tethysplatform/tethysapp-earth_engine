import logging
from tethys_sdk.routing import controller

from ..app import App

log = logging.getLogger(f'tethys.apps.{__name__}')


@controller
def home(request):
    """
    Controller for the app home page.
    """
    context = {}
    return App.render(request, 'home.html', context)


@controller
def about(request):
    """
    Controller for the app about page.
    """
    context = {}
    return App.render(request, 'about.html', context)