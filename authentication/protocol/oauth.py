from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.timezone import datetime, timedelta

import requests

from caslib import OAuthClient
from threepio import auth_logger as logger

from authentication.models import get_or_create_user
from authentication.models import Token as AuthToken
from authentication.settings import auth_settings

User = get_user_model()


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
