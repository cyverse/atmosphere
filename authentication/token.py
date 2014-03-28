from datetime import timedelta

from django.utils import timezone

from rest_framework.authentication import BaseAuthentication

from threepio import logger

from authentication.models import Token as AuthToken
from core.models.user import AtmosphereUser
from authentication.protocol.oauth import get_user_for_token, createOAuthToken
from authentication.protocol.oauth import lookupUser as oauth_lookupUser
from authentication.protocol.oauth import create_user as oauth_create_user
from authentication.protocol.cas import cas_validateUser


class TokenAuthentication(BaseAuthentication):
    """
    Atmosphere 'AuthToken' based authentication.
    To authenticate, pass the token key in the "Authorization"
    HTTP header, prepended with the string "Token ". For example:
        Authorization: Token 098f6bcd4621d373cade4e832627b4f6
    """
    model = AuthToken

    def authenticate(self, request):
        token_key = None
        auth = request.META.get('HTTP_AUTHORIZATION', '').split()
        if len(auth) == 2 and auth[0].lower() == "token":
            token_key = auth[1]
        if not token_key and 'token' in request.session:
            token_key = request.session['token']
        if validate_token(token_key):
            token = self.model.objects.get(key=token_key)
            if token.user.is_active:
                return (token.user, token)
        return None

class OAuthTokenAuthentication(TokenAuthentication):
    """
    OAuthTokenAuthentication:
    To authenticate, pass the token key in the "Authorization" HTTP header,
    prepend with the string "Bearer ". For example:
        Authorization: Bearer 098f6bcd4621d373cade4e832627b4f6
    """
    def authenticate(self, request):
        token_key = None
        auth = request.META.get('HTTP_AUTHORIZATION', '').split()
        if len(auth) == 2 and auth[0].lower() == "bearer":
            oauth_token = auth[1]
            if validate_oauth_token(oauth_token):
                try:
                    token = self.model.objects.get(key=oauth_token)
                except self.model.DoesNotExist:
                    return None
                if token.user.is_active:
                    return (token.user, token)
        return None


def validate_oauth_token(token, request=None):
    """
    Validates the token attached to the request (SessionStorage, GET/POST)
    On every request, ask OAuth to authorize the token
    """
    #Authorization test
    username, expires = get_user_for_token(token)
    if not username:
        return False
    auth_token = createOAuthToken(username, token, expires)
    if not auth_token:
        return False
    return True


def validate_token(token, request=None):
    """
    Validates the token attached to the request (SessionStorage, GET/POST)
    If token has expired,
    CAS will attempt to reauthenticate the user and refresh token.
    Expired Tokens can be used for GET requests ONLY!
    """

    #Existence test
    try:
        auth_token = AuthToken.objects.get(key=token)
        user = auth_token.user
    except AuthToken.DoesNotExist:
        #logger.info("AuthToken <%s> does not exist." % token)
        return False
    if auth_token.is_expired():
        if request and request.META['REQUEST_METHOD'] == 'POST':
            user_to_auth = request.session.get('emulated_by', user)
            if cas_validateUser(user_to_auth):
                #logger.debug("Reauthenticated user -- Token updated")
                auth_token.update_expiration()
                auth_token.save()
                return True
            else:
                logger.warn("Could not reauthenticate user")
                return False
        else:
            #logger.debug("%s using EXPIRED token to GET data.." % user)
            return True
    else:
        return True


### VERSION 1 TOKEN VALIDATION ###

def validate_token1_0(request):
    """
    validates the token attached to the request
    (Opts: in HEADERS || SessionStorage || GET/POST)

    Validate token against the database.
    Check token's time-out to determine authenticity.
    If token has timed out,
    CAS will attempt to reauthenticate the user to renew the token
    Timed out tokens can be used for GET requests ONLY!
    """
    from web import getRequestVars
    request_vars = getRequestVars(request)

    user = request_vars.get('username', None)
    token = request_vars.get('token', None)
    api_server = request_vars.get('api_server', None)
    emulate = request_vars.get('emulate', None)

    if not user or not token:
        #logger.debug("Request Variables missing")
        return False
    try:
        token = AuthToken.objects.get(token=token)
    except AuthToken.DoesNotExist:
        #logger.debug("AuthToken does not exist")
        return False

    tokenExpireTime = timedelta(days=1)
    #Invalid Token
    if token.user != user\
            or token.logout is not None\
            or token.api_server_url != api_server:
        #logger.debug("%s - Token Invalid." % user)
        #logger.debug("%s != %s" % (token.user, user))
        #logger.debug("%s != %s" % (token.api_server_url, api_server))
        #logger.debug("%s is not None" % (token.logout))
        return False

    #Expired Token
    if token.issuedTime + tokenExpireTime < timezone.now():
        if request.META["REQUEST_METHOD"] == "GET":
            #logger.debug("Token Expired - %s requesting GET data OK" % user)
            return True
        #Expired and POSTing data, need to re-authenticate the token
        if emulate:
            user = emulate
        if not cas_validateUser(user):
            #logger.debug("Token Expired - %s was not logged into CAS.")
            return False
        #CAS Reauthentication Success
        #logger.debug("%s reauthenticated with CAS" % user)

    #Valid Token
    token.issuedTime = timezone.now()
    token.save()
    return True
