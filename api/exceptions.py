from rest_framework import status
from rest_framework.response import Response
from rest_framework import exceptions as rest_exceptions
from django.utils.translation import ugettext_lazy as _
from threepio import logger, api_logger

def bad_request(errors, prefix="", status_code=None):
    """
    Expects the output of 'serializer.errors':
    errors = [{'name': 'This is an invalid name'}]
    Returns *all* errors in a single string:
    """
    if not status_code:
        status_code = int(status.HTTP_400_BAD_REQUEST)
    if type(status_code) != int:
        raise Exception("Passed status '%s' is *NOT* an int!" % status_code)

    error_str = ''.join(["%s%s:%s" % (prefix,key,val[0]) for (key,val) in errors.items()])
    error_map = {"errors": [{"code": status_code, "message": error_str }]} # This is an expected format by atmo-airport.
    return Response(error_map,
                    status=status_code)

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


def invalid_auth(message):
    return failure_response(
        status.HTTP_400_BAD_REQUEST,
        "Authentication request refused -- %s" % message)


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
        'or does not exist on Provider %s' % (identity_id, provider_id)
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


def connection_failure(provider_id, identity_id=None):
    logger.warn('Multiple Connection Attempts Failed. '
                'Provider-id:%s Identity-id:%s'
                % (provider_id, identity_id))
    return failure_response(
        status.HTTP_504_GATEWAY_TIMEOUT,
        'Multiple connection attempts to the provider %s have failed. Please'
        ' try again later.' % provider_id)


class ServiceUnavailable(rest_exceptions.APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = _("Service Unavailable.")


def instance_not_found(instance_id):
    return failure_response(
        status.HTTP_404_NOT_FOUND,
        'Instance %s does not exist' % instance_id)


def size_not_available(sna_exception):
    return failure_response(
        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        sna_exception.message)


def inactive_provider(provider_exception):
    return failure_response(
        status.HTTP_409_CONFLICT,
        provider_exception.message)


def over_capacity(capacity_exception):
    return failure_response(
        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        capacity_exception.message)


def under_threshold(threshold_exception):
    return failure_response(
        status.HTTP_400_BAD_REQUEST,
        threshold_exception.message)


def over_quota(quota_exception):
    return failure_response(
        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        quota_exception.message)


def mount_failed(exception):
    return failure_response(
        status.HTTP_409_CONFLICT,
        exception.message)


def over_allocation(allocation_exception):
    return failure_response(
        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        allocation_exception.message)
