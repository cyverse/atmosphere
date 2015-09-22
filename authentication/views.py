"""
authentication response views.
"""
import json
from datetime import datetime
import uuid

from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpResponseRedirect

from threepio import auth_logger as logger

from authentication import createAuthToken, userCanEmulate, cas_loginRedirect
from authentication.models import Token as AuthToken
from authentication.protocol.cas import cas_validateUser
from authentication.protocol.ldap import ldap_validate
from authentication.settings import auth_settings


#GLOBUS Views


def globus_login_redirect(request):
    from authentication.protocol.globus import globus_authorize

    next_url = request.GET.get('next', '/application')
    request.session['next'] = next_url

    return globus_authorize(request)

def globus_callback_authorize(request):
    from authentication.protocol.globus import globus_validate_code
    auth_token = globus_validate_code(request)

    if not auth_token:
        # Redirect out of the OAuth loop
        return login(request)
    request.session['username'] = auth_token.user.username
    request.session['token'] = auth_token.key
    next_url = request.session.get('next', '/application')
    return HttpResponseRedirect(next_url)


#CAS+OAuth Views



def o_callback_authorize(request):
    """
    Authorize a callback from an OAuth IdP
    ( Uses request.META to route which IdP is in use )
    """
    # IF globus --> globus_callback_authorize
    referrer = request.META['HTTP_REFERER']
    if 'globus' in referrer:
        return globus_callback_authorize(request)
    return cas_callback_authorize(request)


def o_login_redirect(request):
    oauth_client = get_cas_oauth_client()
    url = oauth_client.authorize_url()
    return HttpResponseRedirect(url)


def cas_callback_authorize(request):
    """
    Authorize a callback (From CAS IdP)
    """
    logger.info(request.__dict__)
    if 'code' not in request.GET:
        logger.info(request.__dict__)
        # TODO - Maybe: Redirect into a login
        return HttpResponse("")
    oauth_client = get_cas_oauth_client()
    oauth_code = request.GET['code']
    # Exchange code for ticket
    access_token, expiry_date = oauth_client.get_access_token(oauth_code)
    if not access_token:
        logger.info("The Code %s is invalid/expired. Attempting another login."
                    % oauth_code)
        return o_login_redirect(request)
    # Exchange token for profile
    user_profile = oauth_client.get_profile(access_token)
    if not user_profile or "id" not in user_profile:
        logger.error("AccessToken is producing an INVALID profile!"
                     " Check the CAS server and caslib.py for more"
                     " information.")
        # NOTE: Make sure this redirects the user OUT of the loop!
        return login(request)
    # ASSERT: A valid OAuth token gave us the Users Profile.
    # Now create an AuthToken and return it
    username = user_profile["id"]
    auth_token = create_token(username, access_token, expiry_date)
    # Set the username to the user to be emulated
    # to whom the token also belongs
    request.session['username'] = username
    request.session['token'] = auth_token.key
    logger.info("Returning user - %s - to application "
                % username)
    logger.info(request.session.__dict__)
    logger.info(request.user)
    return HttpResponseRedirect(settings.REDIRECT_URL + "/application/")


#Token Authentication Views


@csrf_exempt
def token_auth(request):
    """
    VERSION 2 AUTH
    Authentication is based on the POST parameters:
    * Username (Required)
    * Password (Not Required if CAS authenticated previously)

    NOTE: This authentication is SEPARATE from
    django model authentication
    Use this to give out tokens to access the API
    """
    logger.info('Request to auth')

    token = request.POST.get('token', None)

    username = request.POST.get('username', None)
    # CAS authenticated user already has session data
    # without passing any parameters
    if not username:
        username = request.session.get('username', None)

    password = request.POST.get('password', None)
    # LDAP Authenticate if password provided.
    if username and password:
        if ldap_validate(username, password):
            logger.info("LDAP User %s validated. Creating auth token"
                        % username)
            token = createAuthToken(username)
            expireTime = token.issuedTime + auth_settings.TOKEN_EXPIRY_TIME
            auth_json = {
                'token': token.key,
                'username': token.user.username,
                'expires': expireTime.strftime("%b %d, %Y %H:%M:%S")
            }
            return HttpResponse(
                content=json.dumps(auth_json),
                status=201,
                content_type='application/json')
        else:
            logger.debug("[LDAP] Failed to validate %s" % username)
            return HttpResponse("LDAP login failed", status=401)

    #    logger.info("User %s already authenticated, renewing token"
    #                % username)

    # ASSERT: Token exists here
    if token:
        expireTime = token.issuedTime + auth_settings.TOKEN_EXPIRY_TIME
        auth_json = {
            'token': token.key,
            'username': token.user.username,
            'expires': expireTime.strftime("%b %d, %Y %H:%M:%S")
        }
        return HttpResponse(
            content=json.dumps(auth_json),
            content_type='application/json')

    if not username and not password:
        # The user and password were not found
        # force user to login via CAS
        return cas_loginRedirect(request, '/auth/')

    if cas_validateUser(username):
        logger.info("CAS User %s validated. Creating auth token" % username)
        token = createAuthToken(username)
        expireTime = token.issuedTime + auth_settings.TOKEN_EXPIRY_TIME
        auth_json = {
            'token': token.key,
            'username': token.user.username,
            'expires': expireTime.strftime("%b %d, %Y %H:%M:%S")
        }
        return HttpResponse(
            content=json.dumps(auth_json),
            content_type='application/json')
    else:
        logger.debug("[CAS] Failed to validate - %s" % username)
        return HttpResponse("CAS Login Failure", status=401)


def auth1_0(request):
    """
    VERSION 1 AUTH -- DEPRECATED
    Authentication is based on the values passed in to the header.
    If successful, the request is passed on to auth_response
    CAS Authentication requires: "x-auth-user" AND "x-auth-cas"
    LDAP Authentication requires: "x-auth-user" AND "x-auth-key"

    NOTE(esteve): Should we just always attempt authentication by cas,
    then we dont send around x-auth-* headers..
    """
    logger.debug("Auth Request")
    if 'HTTP_X_AUTH_USER' in request.META\
            and 'HTTP_X_AUTH_CAS' in request.META:
        username = request.META['HTTP_X_AUTH_USER']
        if cas_validateUser(username):
            del request.META['HTTP_X_AUTH_CAS']
            return auth_response(request)
        else:
            logger.debug("CAS login failed - %s" % username)
            return HttpResponse("401 UNAUTHORIZED", status=401)

    if 'HTTP_X_AUTH_KEY' in request.META\
            and 'HTTP_X_AUTH_USER' in request.META:
        username = request.META['HTTP_X_AUTH_USER']
        x_auth_key = request.META['HTTP_X_AUTH_KEY']
        if ldap_validate(username, x_auth_key):
            return auth_response(request)
        else:
            logger.debug("LDAP login failed - %s" % username)
            return HttpResponse("401 UNAUTHORIZED", status=401)
    else:
        logger.debug("Request did not have User/Key"
                     " or User/CAS in the headers")
        return HttpResponse("401 UNAUTHORIZED", status=401)


def auth_response(request):
    """
    Create a new AuthToken for the user, then return the Token & API URL
    AuthTokens will expire after a predefined time
    (See #/auth/utils.py:auth_settings.TOKEN_EXPIRY_TIME)
    AuthTokens will be re-newed if
    the user is re-authenticated by CAS at expiry-time
    """
    logger.debug("Creating Auth Response")
    api_server_url = settings.API_SERVER_URL
    # login validation
    response = HttpResponse()

    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS'
    response['Access-Control-Max-Age'] = 1000
    response['Access-Control-Allow-Headers'] = '*'

    response['X-Server-Management-Url'] = api_server_url
    response['X-Storage-Url'] = "http://"
    response['X-CDN-Management-Url'] = "http://"
    token = str(uuid.uuid4())
    username = request.META['HTTP_X_AUTH_USER']
    response['X-Auth-Token'] = token
    # New code: If there is an 'emulate_user' parameter:
    if 'HTTP_X_EMULATE_USER' in request.META:
        # AND user has permission to emulate
        if userCanEmulate(username):
            logger.debug("EMULATION REQUEST:"
                         "Generating AuthToken for %s -- %s" %
                         (request.META['HTTP_X_EMULATE_USER'],
                          username))
            response['X-Auth-User'] = request.META['HTTP_X_EMULATE_USER']
            response['X-Emulated-By'] = username
            # then this token is for the emulated user
            auth_user_token = AuthToken(
                user=request.META['HTTP_X_EMULATE_USER'],
                issuedTime=datetime.now(),
                remote_ip=request.META['REMOTE_ADDR'],
                api_server_url=api_server_url
            )
        else:
            logger.warn("EMULATION REQUEST:User deemed Unauthorized : %s" %
                        (username,))
            # This user is unauthorized to emulate users - Don't create a
            # token!
            return HttpResponse("401 UNAUTHORIZED TO EMULATE", status=401)
    else:
        # Normal login, no user to emulate
        response['X-Auth-User'] = username
        auth_user_token = AuthToken(
            user=username,
            issuedTime=datetime.now(),
            remote_ip=request.META['REMOTE_ADDR'],
            api_server_url=api_server_url
        )

    auth_user_token.save()
    return response
