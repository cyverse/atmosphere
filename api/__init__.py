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


def _get_init_script(instance_service_url, instance_token,
                     username, init_file_version):
    instance_config = """\
arg = '{
 "atmosphere":{
  "servicename":"instance service",
  "instance_service_url":"%s",
  "server":"%s",
  "token":"%s",
  "userid":"%s",
  "vnc_license":"%s"
 }
}'""" % (instance_service_url, settings.SERVER_URL,
            instance_token, username, settings.ATMOSPHERE_VNC_LICENSE)

    init_script_file = os.path.join(
        settings.PROJECT_ROOT,
        "init_files/%s/atmo-initer.rb" % init_file_version)
    init_script_contents = open(init_script_file).read()
    init_script_contents += instance_config + "\nmain(arg)"
    return init_script_contents


def launch_esh_instance(driver, extras, *args, **kwargs):
    """
    TODO: Remove extras, pass as kwarg_dict instead

    1. Pull the necessary parameters
        machine_alias, size_alias, name
    2. Create a core repr. of the EshInstance
    3. return the eshInstance & instance token
    """
    try:
        #create a reference to this attempted instance launch.
        instance_token = str(uuid.uuid4())

        #Gather the machine object
        machine_alias = extras.get('machine_alias', '')
        machine = driver.get_machine(machine_alias)
        if not machine:
            raise Exception(
                "Machine %s could not be located with this driver"
                % machine_alias)

        #Gather the size object
        size_alias = extras.get('size_alias', '')
        size = driver.get_size(size_alias)
        if not size:
            raise Exception(
                "Size %s could not be located with this driver" % size_alias)

        #Add the user data
        username = extras.get('username', None)
        if not username:
            username = driver.identity.user.username
        if 'name' not in extras:
            extras['name'] = 'Instance of %s' % machine.alias
        if isinstance(driver.provider, EucaProvider):
            instance_service_url = "%s" % (settings.INSTANCE_SERVICE_URL,)
            init_file_version = extras.get('init_file', 30)
            userdata_contents = _get_init_script(instance_service_url,
                                                 instance_token,
                                                 username, init_file_version)
            #Create/deploy the instance -- NOTE: Name is passed in extras
            eshInstance = driver.create_instance(size=size,
                                                 image=machine,
                                                 ex_userdata=userdata_contents,
                                                 **extras)
        elif isinstance(driver.provider, OSProvider):
            extras['deploy'] = True
            extras['token'] = instance_token
            extras['ex_metadata'] = {'tmp_status':'initializing'}
            #Check for project network
            os_driver = OSAccountDriver()
            password = os_driver.hashpass(username)
            project_name = os_driver.get_project_name_for(username)
            os_driver.network_manager\
                     .create_project_network(username,
                                             password,
                                             project_name,
                                             get_cidr=get_uid_number,
                                             **settings.OPENSTACK_NETWORK_ARGS)
            #NOTE: Name, deploy are passed in extras
            #TODO: Explicitly set the kwargs here and pass them instead of args
            #will help avoid confusion here..
            logger.debug("OS Launch params: %s" % extras)
            eshInstance = driver.create_instance(size=size,
                                                 image=machine, **extras)
            # call async tasks.
            task.deploy_init_task(driver, eshInstance)
            #driver.deploy_init_to_task(eshInstance)
        elif isinstance(driver.provider, AWSProvider):
            #TODO:Extra stuff needed for AWS provider here
            extras['deploy'] = True
            extras['token'] = instance_token
            eshInstance = driver.deploy_instance(size=size,
                                                 image=machine, **extras)
        else:
            raise Exception("Unable to launch with this provider.")
        #POST-Provider Hooks
        #OPENSTACK:
        #   - Add floating IP
        #   - Add security group
        return (eshInstance, instance_token)
    except Exception as e:
        logger.exception(e)
        raise


def getEshMap(core_provider):
    try:
        provider_name = core_provider.location.lower()
        return ESH_MAP[provider_name]
    except Exception, e:
        logger.exception(e)
        return None


def getEshProvider(core_provider):
    try:
        eshMap = getEshMap(core_provider)
        provider = eshMap['provider']()
        return provider
    except Exception, e:
        logger.exception(e)
        raise


def get_esh_driver(core_identity, username=None):
    try:
        eshMap = getEshMap(core_identity.provider)
        cred_args = core_identity.credential_list()
        if not username:
            user = core_identity.created_by
        else:
            user = DjangoUser.objects.get(username=username)
        provider = eshMap['provider']()
        #logger.debug("cred_args = %s" % cred_args)
        identity = eshMap['identity'](provider, user=user, **cred_args)
        driver = eshMap['driver'](provider, identity)
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
