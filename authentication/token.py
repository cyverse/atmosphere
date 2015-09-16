import jwt
import re
from urlparse import urlparse

from datetime import timedelta, datetime
from Crypto.PublicKey import RSA
from base64 import b64decode

from django.conf import settings
from django.utils import timezone
from requests.exceptions import ConnectionError
from rest_framework.authentication import BaseAuthentication
from threepio import logger
from authentication import get_or_create_user
from authentication.exceptions import Unauthorized
from authentication.models import Token as AuthToken
from authentication.protocol.cas import cas_validateUser
from authentication.protocol.oauth import cas_profile_for_token,\
    obtainOAuthToken
from core.models.user import AtmosphereUser


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
            # logger.info("AuthToken Obtained for %s:%s" %
            #            (token.user.username, token_key))
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
        if len(auth) == 2 and auth[0].lower() == "bearer":
            jwt_token = auth[1]
            if validate_jwt_token(jwt_token, jwt_assertion, request):
                try:
                    auth_token = self.model.objects.get(key=jwt_token)
                except self.model.DoesNotExist:
                    return None
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
                if token.user.is_active:
                    return (token.user, token)
        return None

def decode_jwt(jwt_token, public_key):
    decoded_pubkey = b64decode(public_key)
    rsa_key = RSA.importKey(decoded_pubkey)
    pem_rsa = rsa_key.exportKey()
    return jwt.decode(jwt_token, pem_rsa)

def extract_path_from_url(url):
    url_parts = urlparse(url)
    # Scheme, netloc/hostname, path (What we want)
    path_parts = url_parts[2].rpartition('/')
    new_path = path_parts[2]  # Left, center, Right (What we want)
    return new_path


def strip_wso2_username(username):
    regexp = re.search(r'agavedev\/(.*)@', username)
    return regexp.group(1)


def wso2_mapping(decoded_message):
    wso2_issuer = 'wso2.org/products/am'
    if decoded_message['iss'] != wso2_issuer:
        return None
    key_conversions = {
        wso2_issuer: {
            'exp': u'expires',
            'lastname': u'last_name',
            'fullname': u'full_name',
            'enduser': u'username',
            'emailaddress': u'email',
            }
        }

    user_profile = {}
    for key, value in decoded_message.items():
        if 'http' in key:
            key = extract_path_from_url(key)
        new_key_name = key_conversions[wso2_issuer].get(key, key)
        if new_key_name == 'username':
            value = strip_wso2_username(value)
        user_profile[new_key_name] = value
    return user_profile

def validate_jwt_token(jwt_token, jwt_assertion, request=None):
    """
    Validates the token attached to the request (SessionStorage, GET/POST)
    On every request, ask JWT to authorize the token
    """
    # Attempt to contact WSO2
    # Ask WSO2 who this token belongs to
    # Map WSO2 user to --> AtmosphereUser
    # return attributes associated with the user (If available)
    #
    from atmosphere.settings import JWT_SP_PUBLIC_KEY_FILE
    with open(JWT_SP_PUBLIC_KEY_FILE,'r') as the_file:
        public_key = the_file.read()
    try:
        decoded_message = decode_jwt(jwt_assertion, public_key)
    except Exception:
        logger.exception("Could not decode JWT Assertion. Check below for more info." % jwt_assertion)
        return False

    user_profile = wso2_mapping(decoded_message)

    username = user_profile.get("username")
    expire_epoch_ms = user_profile.get("expires")
    if not expire_epoch_ms:
        logger.info("Decoded message:%s does not have 'expires' -- check your mappings"
                   % decoded_message)
        return False
    if not username:
        logger.info("Decoded message:%s does not have 'username' -- check your mappings"
                   % decoded_message)
        return False

    # TEST #1 - Timestamps are current
    token_expires = datetime.fromtimestamp(expire_epoch_ms/1000)
    now_time = datetime.now()
    if token_expires <= now_time:
        logger.error("JWT Token is EXPIRED as of %s" % token_expires)
        return False

    # TEST #2 -  Ensure user existence in the correct group
    if 'everyone' not in user_profile.get('role'):
        logger.error("User %s does not have the correct Role. Expected '%s' "
                % (username, 'everyone'))
        return False

    # NOTE: REMOVE this when it is no longer true!
    # Force any username lookup to be in lowercase
    username = username.lower()

    # TEST #3 - Ensure user has an identity
    if not AtmosphereUser.objects.filter(username=username):
        raise Unauthorized("User %s does not yet exist as an AtmosphereUser -- Please create your account FIRST."
                           % username)
    auth_token = create_auth_token(username, jwt_token)
    if not auth_token:
        return False
    return True

def create_auth_token(username, token_key, token_expire=None):
    """
    Using *whatever* representation is necessary for the Token Key
    (Ex: CAS-...., UUID4, JWT-OAuth)
    and the username that the token will belong to
    Create a new AuthToken for DB lookups
    """
    try:
        user = AtmosphereUser.objects.get(username=username)
    except AtmosphereUser.DoesNotExist:
        logger.warn("User %s doesn't exist on the DB. "
                    "JWT Token _NOT_ created" % username)
        return None
    auth_user_token, _ = AuthToken.objects.get_or_create(
        key=token_key, user=user, api_server_url=settings.API_SERVER_URL)
    if token_expire:
        auth_user_token.update_expiration(token_expire)
    auth_user_token.save()
    return auth_user_token

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
    if not AtmosphereUser.objects.filter(username=username):
        raise Unauthorized("User %s does not exist as an AtmosphereUser"
                           % username)
    auth_token = obtainOAuthToken(username, token)
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
    from web import getRequestVars
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
