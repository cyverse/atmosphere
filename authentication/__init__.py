"""
authentication helper methods.
"""
from django.http import HttpResponseRedirect

from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from django.contrib.auth import login, authenticate, get_user_model

from authentication.models import Token as AuthToken
from authentication.settings import auth_settings



def auth_loginRedirect(request, redirect, gateway=False):
    """
    A general login redirection
    :param request: The incoming request
    :param redirect: The absolute/relative path to redirect the user after authentication
    :param gateway: If true, all login attempts should be PASSIVE (that is, the user should not be prompted for a login)
    :return: httpResponseRedirect: User selected area to be redirected
    """
    if hasattr(settings, "ALWAYS_AUTH_USER"):
        return always_auth(request, redirect)
    return cas_loginRedirect(request, redirect, gateway)


def always_auth(request, redirect):
    user = authenticate(
        username=settings.ALWAYS_AUTH_USER,
        password=None,
        request=request)
    login(request, user)
    return HttpResponseRedirect("%s" % (redirect,))


def get_or_create_user(username=None, attributes=None):
    """
    Retrieve or create a User matching the username (No password)
    """
    User = get_user_model()
    if not username:
        return None

    # NOTE: REMOVE this when it is no longer true!
    # Force any username lookup to be in lowercase
    username = username.lower()

    try:
        # Look for the username "EXACT MATCH"
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        user = User.objects.create_user(username, "")
    if attributes:
        user.first_name = attributes['firstName']
        user.last_name = attributes['lastName']
        user.email = attributes['email']
    user.save()
    return user


def createAuthToken(username):
    """
    returns a new token for username
    """
    User = get_user_model()
    # NOTE: REMOVE this when it is no longer true!
    # Force any username lookup to be in lowercase
    if not username:
        return None
    username = username.lower()

    user = User.objects.get(username=username)
    auth_user_token = AuthToken(
        user=user,
        api_server_url=auth_settings.API_SERVER_URL
    )
    auth_user_token.update_expiration()
    auth_user_token.save()
    return auth_user_token


def lookupSessionToken(request):
    """
    Retrieve an existing token from the request session.
    """
    token_key = request.session['token']
    try:
        return AuthToken.objects.get(user=request.user, key=token_key)
    except:
        return None


def validateToken(username, token_key):
    """
    Verify the token belongs to username, and renew it
    """
    auth_user_token = AuthToken.objects.filter(
        user__username=username, key=token_key)
    if not auth_user_token:
        return None
    auth_user_token = auth_user_token[0]
    auth_user_token.update_expiration()
    auth_user_token.save()
    return auth_user_token


def userCanEmulate(username):
    """
    Django users marked as 'staff' have emulate permission
    Additional checks can be added later..
    """
    User = get_user_model()
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return False

    return user.is_staff


# Login Hooks here:
def create_session_token(sender, user, request, **kwargs):
    auth_token = AuthToken(
        user=user,
        api_server_url=auth_settings.API_SERVER_URL
    )
    auth_token.update_expiration()
    auth_token.save()
    request.session['username'] = auth_token.user.username
    request.session['token'] = auth_token.key
    return auth_token


# Instantiate the login hook here.
user_logged_in.connect(create_session_token)
