"""
Atmosphere service utils for rest api.

"""
import uuid
import os.path

from threepio import logger

from rest_framework import status
from rest_framework.response import Response

#Necessary to initialize Meta classes
import rtwo.compute

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


    Throws core.model.Identity.DoesNotExist exceptions if the
    identity, provider or combination of identity and provider
    are invalid.
    """
    core_identity = CoreIdentity.objects.get(provider__id=provider_id,
                                             id=identity_id)
    return get_esh_driver(core_identity)


def failure_response(status, message):
    """
    Return a djangorestframework Response object given an error
    status and message.
    """
    return Response({"errors":
                     {[{'code': status,
                        'message': message}]}},
                    status=status)
