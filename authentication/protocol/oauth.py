from django.utils.timezone import datetime, timedelta

import requests

from caslib import OAuthClient
from threepio import auth_logger as logger

from atmosphere.settings import secrets
from atmosphere import settings
from authentication import get_or_create_user
from authentication.models import Token as AuthToken
from core.models.user import AtmosphereUser


# Requests auth class for access tokens
class TokenAuth(requests.auth.AuthBase):

    """
    Authentication using the protocol:
    Token <access_token>
    """

    def __init__(self, access_token):
        self.access_token = access_token

    def __call__(self, r):
        r.headers['Authorization'] = "Token %s" % self.access_token
        return r


###########################
# CAS-SPECIFIC OAUTH METHODS
###########################
def get_cas_oauth_client():
    o_client = OAuthClient(settings.CAS_SERVER,
                           settings.OAUTH_CLIENT_CALLBACK,
                           settings.OAUTH_CLIENT_KEY,
                           settings.OAUTH_CLIENT_SECRET,
                           auth_prefix=settings.CAS_AUTH_PREFIX)
    return o_client


def cas_profile_contains(attrs, test_value):
    # Two basic types of 'values'
    # Lists: e.g. attrs['entitlement'] = ['group1','group2','group3']
    # Objects: e.g. attrs['email'] = 'test@email.com'
    for attr in attrs:
        for (key, value) in attr.items():
            if isinstance(value, list) and test_value in value:
                return True
            elif value == test_value:
                return True
    return False


def cas_profile_for_token(access_token):
    oauth_client = get_cas_oauth_client()
    profile_map = oauth_client.get_profile(access_token)
    return profile_map
