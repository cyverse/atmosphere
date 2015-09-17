# -*- coding: utf-8 -*-
"""
Core routes used in the application
"""
import os

from django.conf.urls import patterns, url

mobile = os.path.join(os.path.dirname(__file__), 'mobile')
cloud2 = os.path.join(os.path.dirname(__file__), 'cf2')
user_match = "[A-Za-z0-9]+(?:[ _-][A-Za-z0-9]+)*"

urlpatterns = patterns(
    '',
    # "The Front Door"
    url(r'^$', 'core.views.redirectApp'),

    # ADMIN Section:
    # Emulation controls for admin users
    url(r'^api/emulate$', 'core.views.emulate_request'),
    url(r'^api/emulate/(?P<username>(%s))$' %
        user_match, 'core.views.emulate_request'),

    url(r'^admin_login/', 'core.views.redirectAdmin'),
    url(r'^s_login$', 'core.views.s_login'),
    url(r'^login$', 'core.views.login'),
    url(r'^logout$', 'core.views.logout'),

    # GLOBAL Authentication Section:
    #   Login/Logout
    url(r'^oauth2.0/callbackAuthorize$', 'core.views.o_callback_authorize'),
    url(r'^o_login$', 'core.views.o_login_redirect'),

    # The Front-Facing Web Application
    url(r'^application$', 'core.views.app'),

    # Experimental UI
    # TODO: Rename to application when it launches
    # Partials
    url(r'^partials/(?P<path>.*)$', 'core.views.partial'),

    # Error Redirection
    url(r'^no_user$', 'core.views.no_user_redirect'))
