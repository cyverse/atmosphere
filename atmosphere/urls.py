# -*- coding: utf-8 -*-
"""
Routes for the atmosphere application
"""
import os

from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf.urls import patterns, url, include

from api.auth import Authentication

admin.autodiscover()

urlpatterns = patterns(
    '',

    # Core endpoints
    url(r'', include("core.urls", namespace="core")),

    # Authentication
    url(r'', include("authentication.urls", namespace="authentication")),

    # API Layer
    url(r'^api/', include("api.urls", namespace="api")),

    # v2 api auth by token
    url(r'^auth$', Authentication.as_view(), name='token-auth'),

    # API Documentation
    url(r'^api-auth/',
        include('rest_framework.urls', namespace='rest_framework')),

    # DJANGORESTFRAMEWORK
    url(r'^api-token-auth/',
        'rest_framework.authtoken.views.obtain_auth_token'),

    # DB Admin Panel for admin users
    url(r'^admin/', include(admin.site.urls)))

urlpatterns += staticfiles_urlpatterns()
