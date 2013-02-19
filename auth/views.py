"""
authentication response views.

"""

from django.http import HttpResponse
from django.http import HttpResponseRedirect

from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User


from atmosphere import settings
from atmosphere.logger import logger
from auth import createAuthToken, userCanEmulate, cas_loginRedirect
from auth.models import Token as AuthToken
from auth.protocol.ldap import ldap_validate
from auth.protocol.cas import cas_validateUser

from datetime import datetime
import uuid
import json

### VERSION 2 AUTH ###

def token_auth(request):
    """
    Authentication is based on the POST parameters:
    * Username (Required)
    * Password (Not Required if CAS authenticated previously)

    NOTE: This authentication is SEPARATE from django authentication and gives out tokens to access the API
    """

    token = None

    username = request.POST.get('username',None)
    #Handles the case of a CAS authenticated user who already has session data, without passing any parameters
    if not username:
        username = request.session.get('username',None)

    password = request.POST.get('password',None)

    #LDAP Authenticate if password provided.
    if password:
        if ldap_validate(username,password):
            token = createAuthToken(username)
            expireTime = token.issuedTime + settings.TOKEN_EXPIRY_TIME
            auth_json = {'token':token.key, 'username':token.user, 'expires': expireTime.strftime("%b %d, %Y %H:%M:%S")}
            return HttpResponse(content=json.dumps(auth_json), content_type='application/json')
        else:
            logger.debug("[LDAP] Failed to validate %s" % username)
            return HttpResponse("LDAP login failed", status=401)

    #The user and password were not found in POST/session data, force user to login via CAS
    if not username and not password:
        return cas_loginRedirect(request,'/auth/')

    #CAS Authenticate by Proxy (Password not necessary):
    if cas_validate(username):
        token = createAuthToken(username)
        expireTime = token.issuedTime + settings.TOKEN_EXPIRY_TIME
        auth_json = {'token':token.key, 'username':token.user, 'expires': expireTime.strftime("%b %d, %Y %H:%M:%S")}
        return HttpResponse(content=json.dumps(auth_json), content_type='application/json')
    else:
        logger.debug("[CAS] Failed to validate - %s" % username)
        return HttpResponse("CAS Login Failure", status=401)

### VERSION 1 AUTH -- DEPRECATED ###
def auth1_0(request):
    """
    Authentication is based on the values passed in to the header.
    If successful, the request is passed on to auth_response
    CAS Authentication requires: "x-auth-user" AND "x-auth-cas"
    LDAP Authentication requires: "x-auth-user" AND "x-auth-key"

    TODO: Should we just always TRY CAS authentication, so that we dont send around stupid headers like x-auth-cas
    """
    logger.debug("Auth Request")
    if request.META.has_key('HTTP_X_AUTH_USER') and request.META.has_key('HTTP_X_AUTH_CAS') :
        username = request.META['HTTP_X_AUTH_USER']
        if cas_validate(username) == True:
            del request.META['HTTP_X_AUTH_CAS']
            return auth_response(request)
        else:
            logger.debug("CAS login failed - %s" % username)
            return HttpResponse("401 UNAUTHORIZED", status=401)

    if request.META.has_key('HTTP_X_AUTH_KEY') and request.META.has_key('HTTP_X_AUTH_USER') :
        username = request.META['HTTP_X_AUTH_USER']
        x_auth_key = request.META['HTTP_X_AUTH_KEY']
        if ldap_validate(username,x_auth_key) == True:
            return auth_response(request)
        else :
            logger.debug("LDAP login failed - %s" % username)
            return HttpResponse("401 UNAUTHORIZED", status=401)
    else :
        logger.warn("Request did not have User/Key or User/CAS in the headers")
        return HttpResponse("401 UNAUTHORIZED", status=401)

def auth_response(request):
    """
    Create a new AuthToken for the user, then return the Token & API URL
    AuthTokens will expire after a predefined time
    (See #/auth/utils.py:settings.TOKEN_EXPIRY_TIME)
    AuthTokens will be re-newed if the user is re-authenticated by CAS at expiry-time
    """
    logger.debug("Creating Auth Response")
    api_server_url = settings.API_SERVER_URL
    #login validation
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
    #New code: If there is an 'emulate_user' parameter:
    if request.META.has_key('HTTP_X_EMULATE_USER') == True:
    # AND user has permission to emulate
        if userCanEmulate(username):
            logger.warn("EMULATION REQUEST:Generating AuthToken for %s -- %s" % (request.META['HTTP_X_EMULATE_USER'],username))
            response['X-Auth-User'] = request.META['HTTP_X_EMULATE_USER']
            response['X-Emulated-By'] = username
            #then this token is for the emulated user
            auth_user_token = AuthToken(user=request.META['HTTP_X_EMULATE_USER'],issuedTime=datetime.now(),remote_ip=request.META['REMOTE_ADDR'],api_server_url=api_server_url)
        else:
            logger.warn("EMULATION REQUEST:User deemed Unauthorized : %s" % (username,))
            #This user is unauthorized to emulate users - Don't create a token!
            return HttpResponse("401 UNAUTHORIZED TO EMULATE", status=401)
    else:
        #Normal login, no user to emulate
        response['X-Auth-User'] = username
        auth_user_token = AuthToken(user=username,issuedTime=datetime.now(),remote_ip=request.META['REMOTE_ADDR'],api_server_url=api_server_url)

    auth_user_token.save()
    return response
