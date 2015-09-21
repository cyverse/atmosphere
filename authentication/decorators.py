from django.conf import settings
from django.contrib.auth import authenticate, login as django_login
from django.http import HttpResponseRedirect, HttpResponseForbidden

from rest_framework.response import Response
from rest_framework import status

from threepio import auth_logger as logger

from authentication import cas_loginRedirect
from authentication.token import validate_token


def atmo_login_required(func):
    def atmo_login(request, *args, **kwargs):
        if not request:
            logger.debug("[NOREQUEST] User is being logged out because request"
                         " is empty")
            logger.debug("%s\n%s\n%s\n%s" % (request, args, kwargs, func))
            return HttpResponseRedirect(settings.SERVER_URL + "/logout/")

        if not request.session:
            logger.debug("[NOSESSION] User is being logged out because session"
                         " object does not exist in request")
            logger.debug("%s\n%s\n%s\n%s" % (request, args, kwargs, func))
            return HttpResponseRedirect(settings.SERVER_URL + "/logout/")

        if not request.session.get('username'):
            logger.debug("[NOUSER] User is being logged out because session"
                         " did not include a username")
            logger.debug("%s\n%s\n%s\n%s" % (request, args, kwargs, func))
            return HttpResponseRedirect(settings.SERVER_URL + "/logout/")

        # logger.info('atmo_login_required session info: %s'
        #             % request.session.__dict__)
        logger.info('atmo_login_required authentication: %s'
                    % request.session.get('username',
                                          '<Username not in session>'))
        username = request.session.get('username', None)
        token = request.session.get('token', None)
        redirect = kwargs.get('redirect', request.get_full_path())
        emulator = request.session.get('emulated_by', None)

        if emulator:
            logger.info("Test emulator %s instead of %s" %
                        (emulator, username))
            logger.debug(request.session.__dict__)
            # Authenticate the user (Force a CAS test)
            user = authenticate(username=emulator, password="",
                                auth_token=token, request=request)
            # AUTHORIZED STAFF ONLY
            if not user or not user.is_staff:
                return HttpResponseRedirect(settings.SERVER_URL + "/logout/")
            logger.info("Emulate success - Logging in %s" % user.username)
            django_login(request, user)
            return func(request, *args, **kwargs)

        user = authenticate(username=username, password="", auth_token=token,
                            request=request)
        if not user:
            logger.info("Could not authenticate user %s" % username)
            return cas_loginRedirect(request, redirect)
        django_login(request, user)
        return func(request, *args, **kwargs)
    return atmo_login


def atmo_valid_token_required(func):
    def atmo_validate_token(request, *args, **kwargs):
        # Used for requests that require a valid token
        token_key = request.session.get('token')
        if validate_token(token_key, request):
            return func(request, *args, **kwargs)
        else:
            logger.warn('invalid token used')
            return HttpResponseForbidden("403 Forbidden")
    return atmo_validate_token


def validate_request_user(request):
    user = request.user
    return True if user and user.is_authenticated() else False


def api_auth_token_required(func):
    def validate_auth_token(decorated_func, *args, **kwargs):
        request = args[0]
        valid_user = validate_request_user(request)
        if not valid_user:
            logger.debug('Unauthorized access by %s - %s - Invalid Token' %
                         (valid_user, request.META.get('REMOTE_ADDR')))
            return Response(
                "Expected header parameter: Authorization Token <TokenID>",
                status=status.HTTP_401_UNAUTHORIZED)

        return func(request, *args, **kwargs)
    return validate_auth_token


def api_auth_token_optional(func):
    def validate_auth_token(decorated_func, *args, **kwargs):
        """
        Used for requests that require a valid token
        NOTE: Calling request.user for the first time will call `authenticate`
        in the auth.token.TokenAuthentication class
        """
        request = args[0]
        # The result is irrelevant, but
        # the func will be able to
        # use the request.user variable
        request.user.is_authenticated()
        return func(request, *args, **kwargs)
    return validate_auth_token
