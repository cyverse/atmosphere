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

from rtwo.provider import AWSProvider, AWSUSEastProvider,\
    AWSUSWestProvider, EucaProvider,\
    OSProvider, OSValhallaProvider
from rtwo.identity import AWSIdentity, EucaIdentity,\
    OSIdentity
from rtwo.driver import AWSDriver, EucaDriver, OSDriver

from atmosphere import settings

from core.ldap import get_uid_number

from core.models import AtmosphereUser as DjangoUser
from core.models.identity import Identity as CoreIdentity


#These functions return ESH related information based on the core repr
ESH_MAP = {
    'openstack': {
        'provider': OSProvider,
        'identity': OSIdentity,
        'driver': OSDriver
    },
    'eucalyptus':  {
        'provider': EucaProvider,
        'identity': EucaIdentity,
        'driver': EucaDriver
    },
    #TODO: Fix this line when we use AWS
    'ec2_us_east':  {
        'provider': AWSUSEastProvider,
        'identity': AWSIdentity,
        'driver': AWSDriver
    },
    'ec2_us_west':  {
        'provider': AWSUSWestProvider,
        'identity': AWSIdentity,
        'driver': AWSDriver
    },
}


def get_esh_map(core_provider):
    """
    Based on the type of cloud: (OStack, Euca, AWS)
    initialize the provider/identity/driver from 'the map'
    """
    try:
        provider_name = core_provider.type.name.lower()
        return ESH_MAP[provider_name]
    except Exception, e:
        logger.exception(e)
        return None


def get_esh_provider(core_provider):
    try:
        esh_map = get_esh_map(core_provider)
        provider = esh_map['provider'](identifier=core_provider.location)
        return provider
    except Exception, e:
        logger.exception(e)
        raise


def get_esh_driver(core_identity, username=None):
    try:
        core_provider = core_identity.provider
        esh_map = get_esh_map(core_provider)
        if not username:
            user = core_identity.created_by
        else:
            user = DjangoUser.objects.get(username=username)
        provider = get_esh_provider(core_provider)
        provider_creds = core_identity.provider.get_esh_credentials(provider)
        identity_creds = core_identity.get_credentials()
        identity = esh_map['identity'](provider, user=user, **identity_creds)
        driver = esh_map['driver'](provider, identity, **provider_creds)
        return driver
    except Exception, e:
        logger.exception(e)
        raise


def prepare_driver(request, provider_id, identity_id):
    """
    Return an rtwo.EshDriver for the given provider_id
    and identity_id.

    If invalid credentials, provider_id or identity_id is
    used return None.
    """
    try:
        identity = CoreIdentity.objects.get(provider__id=provider_id,
                                            id=identity_id)
        if identity in request.user.identity_set.all():
            return get_esh_driver(identity)
    except ObjectDoesNotExist:
        pass


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


def invalid_creds(provider_id, identity_id):
    logger.warn('Authentication Failed. Provider-id:%s Identity-id:%s'
                % (provider_id, identity_id))
    return failure_response(
        status.HTTP_401_UNAUTHORIZED,
        'Identity/Provider Authentication Failed')
