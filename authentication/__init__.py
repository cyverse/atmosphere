"""
authentication helper methods.
"""

from django.conf import settings
from django.contrib.auth.signals import user_logged_in

from authentication.models import Token as AuthToken, create_token
from authentication.settings import auth_settings


# Login Hooks here:
def create_session_token(sender, user, request, issuer="Django-Session", **kwargs):
    auth_token = create_token(user, issuer=issuer)
    auth_token.update_expiration() # 2hr default expiry
    auth_token.save()
    request.session['username'] = auth_token.user.username
    request.session['token'] = auth_token.key
    return auth_token


# Instantiate the login hook here.
user_logged_in.connect(create_session_token)
