import logging
from django.shortcuts import render
from tethys_sdk.permissions import login_required

log = logging.getLogger(f'tethys.apps.{__name__}')


@login_required()
def home(request):
    """
    Controller for the app home page.
    """
    context = {}
    return render(request, 'earth_engine/home.html', context)


@login_required()
def about(request):
    """
    Controller for the app about page.
    """
    context = {}
    return render(request, 'earth_engine/about.html', context)
