# -*- coding: utf-8 -*-
"""
Core routes used in the application
"""
import os

from django.conf.urls import url
from core import views

mobile = os.path.join(os.path.dirname(__file__), 'mobile')
cloud2 = os.path.join(os.path.dirname(__file__), 'cf2')
user_match = "[A-Za-z0-9]+(?:[ _-][A-Za-z0-9]+)*"

urlpatterns = [
    # Emulation controls for admin users
    url(r'^api/emulate$', views.emulate_request),
    url(r'^api/emulate/(?P<username>(%s))$' %
        user_match, views.emulate_request)
]
