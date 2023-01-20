import logging
from django.shortcuts import render
from tethys_sdk.routing import controller

log = logging.getLogger(f'tethys.apps.{__name__}')


@controller
def home(request):
    """
    Controller for the app home page.
    """
    context = {}
    return render(request, 'earth_engine/home.html', context)


@controller
def about(request):
    """
    Controller for the app about page.
    """
    context = {}
    return render(request, 'earth_engine/about.html', context)
