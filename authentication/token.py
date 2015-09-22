# -*- coding: utf-8 -*-
"""
Token based authentication
"""
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from requests.exceptions import ConnectionError
from rest_framework.authentication import BaseAuthentication
from threepio import logger
from authentication import get_or_create_user
from authentication.exceptions import Unauthorized
from authentication.models import Token as AuthToken,\
     create_token
from authentication.protocol.cas import cas_validateUser
from authentication.protocol.oauth import cas_profile_for_token
from authentication.protocol.wso2 import WSO2_JWT

User = get_user_model()


def getRequestParams(request):
    """
    Extracts paramters from GET/POST in a Django Request object
    """
    if request.META['REQUEST_METHOD'] == 'GET':
        try:
            # Will only succeed if a GET method with items
            return dict(request.GET.items())
        except:
            pass
    elif request.META['REQUEST_METHOD'] == 'POST':
        try:
            # Will only succeed if a POST method with items
            return dict(request.POST.items())
        except:
            pass
    logger.debug("REQUEST_METHOD is neither GET or POST.")


def getRequestVars(request):
    """
    Extracts parameters from a Django Request object
    Expects ALL or NOTHING. You cannot mix data!
    """
    username = None
    token = None
    api_server = None
    emulate = None
    try:
        # Attempt #1 - SessionStorage - Most reliable
        logger.debug(request.session.items())
        username = request.session['username']
        token = request.session['token']
        api_server = request.session['api_server']
        emulate = request.session.get('emulate', None)
        return {'username': username, 'token': token, 'api_server': api_server,
                'emulate': emulate}
    except KeyError:
        pass
    try:
        # Attempt #2 - Header/META values, this is DEPRECATED as of v2!
        logger.debug(request.META.items())
        username = request.META['HTTP_X_AUTH_USER']
        token = request.META['HTTP_X_AUTH_TOKEN']
        api_server = request.META['HTTP_X_API_SERVER']
        emulate = request.META.get('HTTP_X_AUTH_EMULATE', None)
        return {'username': username, 'token': token,
                'api_server': api_server, 'emulate': emulate}
    except KeyError:
        pass
    try:
        # Final attempt - GET/POST values
        params = getRequestParams(request)
        logger.debug(params.items())
        username = params['HTTP_X_AUTH_USER']
        token = params['HTTP_X_AUTH_TOKEN']
        api_server = params['HTTP_X_API_SERVER']
        emulate = params.get('HTTP_X_AUTH_EMULATE', None)
        return {'username': username, 'token': token,
                'api_server': api_server, 'emulate': emulate}
    except KeyError:
        pass
    return None


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


class JWTTokenAuthentication(TokenAuthentication):

    """
    JWTTokenAuthentication:
    To authenticate, pass the token key in the "Authorization" HTTP header,
    prepend with the string "Bearer ". For example:
        Authorization: Bearer 098f6bcd4621d373cade4e832627b4f6
    """

    def authenticate(self, request):
        auth = request.META.get('HTTP_AUTHORIZATION', '').split()
        jwt_assertion = request.META.get('HTTP_ASSERTION')
        if jwt_assertion:
            sp = WSO2_JWT(settings.JWT_SP_PUBLIC_KEY_FILE)
            auth_token = sp.create_token_from_jwt(jwt_assertion)
            if auth_token.user.is_active:
                return (auth_token.user, auth_token)
        return None


class OAuthTokenAuthentication(TokenAuthentication):

    """
    OAuthTokenAuthentication:
    To authenticate, pass the token key in the "Authorization" HTTP header,
    prepend with the string "Token ". For example:
        Authorization: Token 098f6bcd4621d373cade4e832627b4f6
    """

    def _mock_oauth_login(self, oauth_token):
        username = settings.ALWAYS_AUTH_USER
        user = get_or_create_user(username, {
            'firstName': "Mocky Mock",
            'lastName': "MockDoodle",
            'email': '%s@iplantcollaborative.org' % settings.ALWAYS_AUTH_USER,
            'entitlement': []})
        _, token = self.model.objects.get_or_create(key=oauth_token, user=user)
        return user, token

    def authenticate(self, request):
        all_backends = settings.AUTHENTICATION_BACKENDS
        auth = request.META.get('HTTP_AUTHORIZATION', '').split()
        if len(auth) == 2 and auth[0].lower() == "token":
            oauth_token = auth[1]
            if 'authentication.authBackends.MockLoginBackend' in all_backends:
                user, token = self._mock_oauth_login(oauth_token)
                return (user, token)
            if validate_oauth_token(oauth_token):
                try:
                    token = self.model.objects.get(key=oauth_token)
                except self.model.DoesNotExist:
                    return None
                if token and token.user.is_active:
                    return (token.user, token)
        return None
def validate_oauth_token(token, request=None):
    """
    Validates the token attached to the request (SessionStorage, GET/POST)
    On every request, ask OAuth to authorize the token
    """
    # Attempt to contact CAS
    try:
        user_profile = cas_profile_for_token(token)
    except ConnectionError:
        logger.exception("CAS could not be reached!")
        user_profile = None

    if not user_profile:
        return False
    username = user_profile.get("id")
    if not username:
        # logger.info("Invalid Profile:%s does not have username/attributes"
        #            % user_profile)
        return False

    # NOTE: REMOVE this when it is no longer true!
    # Force any username lookup to be in lowercase
    if not username:
        return None
    username = username.lower()

    # TEST 1 : Must be in the group 'atmo-user'
    # NOTE: Test 1 will be IGNORED until we can verify it returns 'entitlement'
    # EVERY TIME!
    #    raise Unauthorized("User %s is not a member of group 'atmo-user'"
    #                       % username)
    # TODO: TEST 2 : Must have an identity (?)
    if not User.objects.filter(username=username):
        raise Unauthorized("User %s does not exist as an User"
                           % username)
    auth_token = create_token(username, token)
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

    # Existence test
    try:
        auth_token = AuthToken.objects.get(key=token)
        user = auth_token.user
    except AuthToken.DoesNotExist:
        logger.info("AuthToken Retrieved:%s Does not exist." % (token,))
        return False
    if auth_token.is_expired():
        if request and request.META['REQUEST_METHOD'] != 'GET':
            # See if the user (Or the user who is emulating a user) can be
            # re-authed.
            user_to_auth = request.session.get('emulated_by', user)
            if cas_validateUser(user_to_auth):
                auth_token.update_expiration()
                auth_token.save()
                return True
            else:
                logger.info("Token %s expired, User %s "
                            "could not be reauthenticated in CAS"
                            % (token, user))
                return False
        else:
            logger.debug("Token %s EXPIRED, but allowing User %s to GET data.."
                         % (token, user))
            return True
    else:
        return True


# VERSION 1 TOKEN VALIDATION

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
    request_vars = getRequestVars(request)

    user = request_vars.get('username', None)
    token = request_vars.get('token', None)
    api_server = request_vars.get('api_server', None)
    emulate = request_vars.get('emulate', None)

    if not user or not token:
        return False
    try:
        token = AuthToken.objects.get(token=token)
    except AuthToken.DoesNotExist:
        return False

    tokenExpireTime = timedelta(days=1)
    # Invalid Token
    if token.user != user\
            or token.logout is not None\
            or token.api_server_url != api_server:
        return False

    # Expired Token
    if token.issuedTime + tokenExpireTime < timezone.now():
        if request.META["REQUEST_METHOD"] == "GET":
            return True
        # Expired and POSTing data, need to re-authenticate the token
        if emulate:
            user = emulate
        if not cas_validateUser(user):
            return False
        # CAS Reauthentication Success

    # Valid Token
    token.issuedTime = timezone.now()
    token.save()
    return True
