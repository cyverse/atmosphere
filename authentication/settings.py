# -*- coding: utf-8 -*-
"""
Settings for the authentication app.
"""
from datetime import timedelta

from django.conf import settings
from django.test.signals import setting_changed


USER_SETTINGS = getattr(settings, 'AUTHENTICATION', {})


DEFAULTS =  {
    # General
    "TOKEN_EXPIRY_TIME": timedelta(days=1),
    "CAS_SERVER": None,
    "API_SERVER_URL": None,

    # OAUTH
    "OAUTH_CLIENT_KEY": None,
    "OAUTH_CLIENT_SECRET": None,
    "OAUTH_CLIENT_CALLBACK": None,
    "OAUTH_PRIVATE_KEY": None,
    "OAUTH_ISSUER_USER": None,
    "OAUTH_SCOPE": None,
    "OAUTH_GROUPY_SERVER": None,

    # LDAP
    "LDAP_SERVER": None,
    "LDAP_SERVER_DN": None
}


class ReadOnlyAttrDict(dict):
    __getattr__ = dict.__getitem__

new_settings = DEFAULTS.copy()
new_settings.update(USER_SETTINGS)
auth_settings = ReadOnlyAttrDict(new_settings)


def reload_settings(*args, **kwargs):
    global auth_settings
    setting_name, value = kwargs['setting'], kwargs['value']
    if setting_name == "AUTHENTICATION":
        defaults = DEFAULTS.copy()
        auth_setings = ReadOnlyAttrDict(defaults.update(values))


setting_changed.connect(reload_settings)
