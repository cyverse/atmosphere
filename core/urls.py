# -*- coding: utf-8 -*-
"""
Core routes used in the application
"""
from django.conf.urls import url
from core import views

user_match = "[A-Za-z0-9]+(?:[ _-][A-Za-z0-9]+)*"

urlpatterns = [
    # Emulation controls for admin users
    url(r'^api/emulate$', views.emulate_request),
    url(
        r'^api/emulate/(?P<username>(%s))$' % user_match, views.emulate_request
    )
]
