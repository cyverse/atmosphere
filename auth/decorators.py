# django http libraries
from django.contrib.auth import authenticate, login as django_login
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotFound, HttpResponseForbidden

#rest framework libraries
from rest_framework.response import Response
from rest_framework import status

# atmosphere libraries
from atmosphere import settings
from atmosphere.logger import logger

from auth import cas_loginRedirect
from auth.token import validate_token

def atmo_login_required(func):
    def atmo_login(request, *args, **kwargs):
        """
        Django Requests need to be formally logged in to Django
        However, WHO needs to be authenticated is determined by the available server session data
        @redirect - location to redirect user after logging in
        """
        #logger.debug("%s\n%s\n%s\n%s" % (request, args, kwargs, func))
        if request is None or request.session is None:
            return HttpResponseRedirect(settings.SERVER_URL+"/logout/")

        username = request.session.get('username',None)
        redirect = kwargs.get('redirect',request.get_full_path())
        emulator = request.session.get('emulated_by',None)
        #logger.info("%s\n%s\n%s" % (username, redirect, emulator))

        if emulator:
            logger.info("Emulator login -- Test %s for login instead of %s" % (emulator,username))
            logger.debug(request.session.__dict__)
			#Authenticate the user (Force a CAS test)
            user = authenticate(username=emulator, password="")
            #AUTHORIZED STAFF ONLY
            if not user or not user.is_staff:
                return HttpResponseRedirect(settings.SERVER_URL+"/logout/")
            logger.info("Emulate success - Logging in %s" % user.username)
            django_login(request, user)
            return func(request, *args, **kwargs)


        user = authenticate(username=username, password="")
        if not user:
            logger.info("Could not authenticate user %s" % username)
            return cas_loginRedirect(request, redirect)
        django_login(request, user)
        return func(request, *args, **kwargs)
    return atmo_login

def atmo_valid_token_required(func):
    """
    Use this decorator to authenticate WSGIRequest objects (Legacy..Supported)
    """
    def atmo_validate_token(request, *args, **kwargs):
        """
        Used for requests that require a valid token
        """
        token_key = request.session['token']
        if validate_token(token_key, request):
            return func(request, *args, **kwargs)
        else:
            logger.debug('invalid token used')
            return HttpResponseForbidden("403 Forbidden")
    return atmo_validate_token

def api_auth_token_required(func):
    """
    Use this decorator to authenticate rest_framework.request.Request objects
    """
    def validate_auth_token(decorated_func, *args, **kwargs):
        """
        Used for requests that require a valid token
        NOTE: Calling request.user for the first time will call 'authenticate' 
            in the auth.token.TokenAuthentication class
        """
        request = args[0]
        logger.info("Validating auth token")
        user = request.user
        logger.info(user)
        auth = request.auth
        if user and user.is_authenticated():
            return func(request, *args, **kwargs)
        else:
            logger.debug('invalid token used')
            return Response("Invalid Token. Expected header parameter: Authorization Token <TokenID>", status=status.HTTP_401_UNAUTHORIZED)
    return validate_auth_token
