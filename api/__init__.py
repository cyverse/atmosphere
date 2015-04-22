"""
Atmosphere service utils for rest api.

"""
from functools import wraps
import uuid
import os.path

from django.core.exceptions import ObjectDoesNotExist

from rest_framework import status
from rest_framework.response import Response

from threepio import logger, api_logger

import rtwo.compute  # Necessary to initialize Meta classes

from core.models import AtmosphereUser as User

def emulate_user(func):
    """
    Support for staff users to emulate a specific user history.

    This decorator is specifically for use with an APIView.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        emulate_name = self.request.query_params.get('username', None)
        if self.request.user.is_staff and emulate_name:
            emualate_name = emulate_name[0]  # Querystring conversion
            original_user = self.request.user
            try:
                self.request.user = User.objects.get(username=emulate_name)
                self.emulated = (True, original_user, emulate_name)
            except User.DoesNotExist:
                self.emulated = (False, original_user, emulate_name)
        return func(self, *args,**kwargs)
    return wrapper


def failure_response(status, message):
    """
    Return a djangorestframework Response object given an error
    status and message.
    """
    api_logger.info("status: %s message: %s" % (status, message))
    return Response({"errors":
                     [{'code': status,
                       'message': message}]},
                    status=status)


def malformed_response(provider_id, identity_id):
    logger.warn('Server provided bad response. Provider-id:%s Identity-id:%s'
                % (provider_id, identity_id))
    return failure_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "Cloud Communications Error --"
        " Contact your Cloud Administrator OR try again later!")

def invalid_provider(provider_id):
    log_message = 'Provider %s is inactive, disabled, or does not exist.'\
                % (provider_id, )
    logger.warn(log_message)
    return failure_response(
        status.HTTP_401_UNAUTHORIZED,
        log_message)

def invalid_provider_identity(provider_id, identity_id):
    log_message = 'Identity %s is inactive, disabled, '\
            'or does not exist on Provider %s'\
                % (identity_id, provider_id)
    logger.warn(log_message)
    return failure_response(
        status.HTTP_401_UNAUTHORIZED,
        log_message)

def invalid_creds(provider_id, identity_id):
    logger.warn('Authentication Failed. Provider-id:%s Identity-id:%s'
                % (provider_id, identity_id))
    return failure_response(
        status.HTTP_401_UNAUTHORIZED,
        'Identity/Provider Authentication Failed')

def connection_failure(provider_id, identity_id):
    logger.warn('Multiple Connection Attempts Failed. Provider-id:%s Identity-id:%s'
                % (provider_id, identity_id))
    return failure_response(
        status.HTTP_504_GATEWAY_TIMEOUT,
        'Multiple connection attempts to the provider %s have failed. Please'
        ' try again later.' % provider_id)
