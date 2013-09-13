"""
Atmosphere service utils for rest api.

"""

import uuid
import os.path

#Necessary to initialize Meta classes
import rtwo.compute

from django.contrib.auth.models import User as DjangoUser

from threepio import logger

from atmosphere import settings

from core.ldap import get_uid_number

from core.models.identity import Identity as CoreIdentity
from core.models.instance import update_instance_metadata

from rtwo.provider import AWSProvider, AWSUSEastProvider,\
    AWSUSWestProvider, EucaProvider,\
    OSProvider, OSValhallaProvider
from rtwo.identity import AWSIdentity, EucaIdentity,\
    OSIdentity
from rtwo.driver import AWSDriver, EucaDriver, OSDriver

from service.accounts.openstack import AccountDriver as OSAccountDriver
from service import task

#These functions return ESH related information based on the core repr
ESH_MAP = {
    'openstack': {
        'provider': OSValhallaProvider,
        'identity': OSIdentity,
        'driver': OSDriver
    },
    'eucalyptus':  {
        'provider': EucaProvider,
        'identity': EucaIdentity,
        'driver': EucaDriver
    },
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
    try:
        provider_name = core_provider.location.lower()
        return ESH_MAP[provider_name]
    except Exception, e:
        logger.exception(e)
        return None


def get_esh_provider(core_provider):
    try:
        esh_map = get_esh_map(core_provider)
        provider = esh_map['provider']()
        return provider
    except Exception, e:
        logger.exception(e)
        raise


def get_esh_driver(core_identity, username=None):
    try:
        esh_map = get_esh_map(core_identity.provider)
        cred_args = core_identity.credential_list()
        if not username:
            user = core_identity.created_by
        else:
            user = DjangoUser.objects.get(username=username)
        provider = esh_map['provider']()
        #logger.debug("cred_args = %s" % cred_args)
        identity = esh_map['identity'](provider, user=user, **cred_args)
        driver = esh_map['driver'](provider, identity)
        return driver
    except Exception, e:
        logger.exception(e)
        raise


def prepare_driver(request, identity_id):
    """
    TODO: Cache driver based on specific provider
    return esh_driver
    """
    username = request.user
    core_identity = CoreIdentity.objects.get(id=identity_id)
    esh_driver = get_esh_driver(core_identity, username)
    return esh_driver


def failureJSON(errors, *args, **kwargs):
    """
    Input : List of errors (human readable)
    Output: Structured JSON object to contain the errors
    TODO: Determine if this is useful or a wash..
    """
    return {'errors': errors}
