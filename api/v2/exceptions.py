# These exceptions will be used *Exclusively* for API v2.
# They may be migrated back into api/exceptions.py when v1 is deprecated.
from rest_framework import status
from rest_framework.response import Response
from threepio import logger, api_logger

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


def invalid_creds(identity):
    provider_id = identity.provider.uuid
    identity_id = identity.id
    logger.warn('Authentication Failed. Provider-id:%s Identity-id:%s'
                % (provider_id, identity_id))
    return failure_response(
        status.HTTP_401_UNAUTHORIZED,
        'Identity/Provider Authentication Failed')


def connection_failure(identity):
    provider_id = identity.provider.uuid
    identity_id = identity.id
    logger.warn('Multiple Connection Attempts Failed. '
                'Provider-id:%s Identity-id:%s'
                % (provider_id, identity_id))
    return failure_response(
        status.HTTP_504_GATEWAY_TIMEOUT,
        'Multiple connection attempts to the provider %s have failed. Please'
        ' try again later.' % provider_id)


