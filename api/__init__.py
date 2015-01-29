"""
Atmosphere service utils for rest api.

"""
import uuid
import os.path

from django.core.exceptions import ObjectDoesNotExist

from rest_framework import status
from rest_framework.response import Response

from threepio import logger, api_logger

import rtwo.compute  # Necessary to initialize Meta classes


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
