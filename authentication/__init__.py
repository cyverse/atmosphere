"""
authentication helper methods.

"""
from django.http import HttpResponseRedirect

from atmosphere import settings

from authentication.models import Token as AuthToken
from core.models import AtmosphereUser as User


def cas_logoutRedirect():
    return HttpResponseRedirect(settings.CAS_SERVER +
                                "/cas/logout?service="+settings.SERVER_URL)


def cas_loginRedirect(request, redirect=None, gateway=False):
    if not redirect:
        redirect = request.get_full_path()
    login_url = settings.CAS_SERVER +\
        "/cas/login?service="+settings.SERVER_URL +\
        "/CAS_serviceValidater?sendback="+redirect
    if gateway:
        login_url += '&gateway=true'
    return HttpResponseRedirect(login_url)


def get_or_create_user(username=None, attributes=None):
    """
    Retrieve or create a User matching the username (No password)
    """
    if not username:
        return None
    try:
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
    user = User.objects.get(username=username)
    auth_user_token = AuthToken(
        user=user,
        api_server_url=settings.API_SERVER_URL
    )
    auth_user_token.update_expiration()
    auth_user_token.save()
    return auth_user_token
                   

def validateToken(username, token_key):
    """
    Verify the token belongs to username, and renew it
    """
    auth_user_token = AuthToken.objects.filter(user__username=username, key=token_key)
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
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return False

    return user.is_staff
