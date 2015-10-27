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

    # Authentication endpoints
    url(r'', include("iplantauth.urls", namespace="iplantauth")),

    # API Layer endpoints
    url(r'^api/', include("api.urls", namespace="api")),

    # v2 API auth by token
    url(r'^auth$', Authentication.as_view(), name='token-auth'),

    # DRF API Login/Logout
    url(r'^api-auth/',
        include('rest_framework.urls', namespace='rest_framework')),

    # Token login (Used internally by DRF?)
    url(r'^api-token-auth/',
        'rest_framework.authtoken.views.obtain_auth_token'),

    # DB Admin Panel for admin users
    url(r'^admin/', include(admin.site.urls)))

from django.conf import settings

if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns += (
            url(r'^__debug__/', include(debug_toolbar.urls)),
            )
    except ImportError:
        pass

urlpatterns += staticfiles_urlpatterns()
