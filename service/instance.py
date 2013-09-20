import uuid
import os.path

from rtwo.provider import AWSProvider, AWSUSEastProvider,\
    AWSUSWestProvider, EucaProvider,\
    OSProvider, OSValhallaProvider
from rtwo.driver import OSDriver
from threepio import logger

from core.models.identity import Identity as CoreIdentity
from core.models.instance import convert_esh_instance
from core.models.size import convert_esh_size

from atmosphere import settings

from api import get_esh_driver

from service import task
from service.quota import check_over_quota
from service.allocation import check_over_allocation
from service.exceptions import OverAllocationError, OverQuotaError
from service.accounts.openstack import AccountDriver as OSAccountDriver


def stop_instance(esh_driver, esh_instance, provider_id, identity_id, user):
    """

    raise OverQuotaError, OverAllocationError, InvalidCredsError
    """
    esh_driver.stop_instance(esh_instance)
    update_status(esh_driver, esh_instance.id, provider_id, identity_id, user)

def start_instance(esh_driver, esh_instance, provider_id, identity_id, user):
    """

    raise OverQuotaError, OverAllocationError, InvalidCredsError
    """
    esh_driver.start_instance(esh_instance)
    update_status(esh_driver, esh_instance.id, provider_id, identity_id, user)

def suspend_instance(esh_driver, esh_instance, provider_id, identity_id, user):
    """

    raise OverQuotaError, OverAllocationError, InvalidCredsError
    """
    esh_driver.suspend_instance(esh_instance)
    update_status(esh_driver, esh_instance.id, provider_id, identity_id, user)

def resume_instance(esh_driver, esh_instance, provider_id, identity_id, user):
    """

    raise OverQuotaError, OverAllocationError, InvalidCredsError
    """
    check_quota(user.username, identity_id, esh_instance.size)
    esh_driver.resume_instance(esh_instance)
    update_status(esh_driver, esh_instance.id, provider_id, identity_id, user)

def update_status(esh_driver, instance_id, provider_id, identity_id, user):
    #Grab a new copy of the instance
    esh_instance = esh_driver.get_instance(instance_id)
    #Convert & Update based on new status change
    core_instance = convert_esh_instance(esh_driver,
                                       esh_instance,
                                       provider_id,
                                       identity_id,
                                       user)
    core_instance.update_history(
        core_instance.esh.extra['status'],
        core_instance.esh.extra.get('task'))

def destroy_instance(identity_id, instance_alias):
    core_identity = CoreIdentity.objects.get(id=identity_id)
    esh_driver = get_esh_driver(core_identity)
    instance = esh_driver.get_instance(instance_alias)
    if isinstance(esh_driver, OSDriver):
        #Openstack: Remove floating IP first
        esh_driver._connection.ex_disassociate_floating_ip(instance)
    node_destroyed = esh_driver._connection.destroy_node(instance)
    return node_destroyed


def launch_instance(user, provider_id, identity_id, size_alias, machine_alias, **kwargs):
    """
    Required arguments will launch the instance, extras will do
    provider-specific modifications.

    Test the quota, Launch the instance, creates a core repr and updates status.

    returns a core_instance object after updating core DB.
    """

    core_identity = CoreIdentity.objects.get(id=identity_id)

    esh_driver = get_esh_driver(core_identity, user)
    size = esh_driver.get_size(size_alias)

    #May raise SizeNotAvailable
    check_size(size, provider_id)

    #May raise OverQuotaError or OverAllocationError
    check_quota(user.username, identity_id, size)

    #May raise InvalidCredsError
    (esh_instance, token) = launch_esh_instance(esh_driver, machine_alias,
                                                size_alias, core_identity,
                                                **kwargs)
    #Convert esh --> core
    core_instance = convert_esh_instance(
        esh_driver, esh_instance, provider_id, identity_id, user, token)
    core_instance.update_history(
        core_instance.esh.extra['status'],
        #2nd arg is task OR tmp_status
        core_instance.esh.extra.get('task') or\
        core_instance.esh.extra.get('metadata',{}).get('tmp_status'),
        first_update=True)

    return core_instance

def check_size(esh_size, provider_id):
    try:
        if not convert_esh_size(esh_size, provider_id).active():
            raise SizeNotAvailable()
    except:
        raise SizeNotAvailable()

def check_quota(username, identity_id, esh_size):
    (over_quota, resource,\
     requested, used, allowed) = check_over_quota(username,
                                                  identity_id,
                                                  esh_size)
    if over_quota:
        raise OverQuotaError(resource, requested, used, allowed)
    (over_allocation, time_diff) = check_over_allocation(username,
                                                         identity_id)
    if over_allocation:
        raise OverAllocationError(time_diff)

def network_init(core_identity):
    os_driver = OSAccountDriver(core_identity.provider)
    os_driver.create_network(core_identity)

def launch_esh_instance(driver, machine_alias, size_alias, core_identity, 
                        name=None, username=None, *args, **kwargs):
    """
    TODO: Remove extras, pass as kwarg_dict instead

    return the esh_instance & instance token
    """
    try:
        #create a reference to this attempted instance launch.
        instance_token = str(uuid.uuid4())

        #Gather the machine object
        machine = driver.get_machine(machine_alias)
        if not machine:
            raise Exception(
                "Machine %s could not be located with this driver"
                % machine_alias)

        #Gather the size object
        size = driver.get_size(size_alias)
        if not size:
            raise Exception(
                "Size %s could not be located with this driver" % size_alias)

        if not username:
            username = driver.identity.user.username
        if not name:
            name = 'Instance of %s' % machine.alias

        if isinstance(driver.provider, EucaProvider):
            #Create and set userdata
            instance_service_url = "%s" % (settings.INSTANCE_SERVICE_URL,)
            init_file_version = kwargs.get('init_file', 30)
            userdata_contents = _get_init_script(instance_service_url,
                                                 instance_token,
                                                 name,
                                                 username, init_file_version)
            #Create/deploy the instance -- NOTE: Name is passed in extras
            logger.info("EUCA -- driver.create_instance EXTRAS:%s" % kwargs)
            esh_instance = driver\
                .create_instance(name=name, image=machine,
                                 size=size, ex_userdata=userdata_contents,
                                 **kwargs)
        elif isinstance(driver.provider, OSProvider):
            deploy = True
            ex_metadata = {'tmp_status': 'initializing'}
            #Check for project network.. TODO: Fix how password/project are
            # retrieved
            network_init(core_identity)
            logger.debug("OS driver.create_instance kwargs: %s" % kwargs)
            esh_instance = driver.create_instance(name=name, image=machine,
                                                  size=size, token=instance_token,
                                                  ex_metadata=ex_metadata,
                                                  deploy=True, **kwargs)
            # call async task to deploy to instance.
            task.deploy_init_task(driver, esh_instance)
        elif isinstance(driver.provider, AWSProvider):
            #TODO:Extra stuff needed for AWS provider here
            esh_instance = driver.deploy_instance(name=name, image=machine,
                                                  size=size, deploy=True,
                                                  token=instance_token,
                                                  **kwargs)
        else:
            raise Exception("Unable to launch with this provider.")
        return (esh_instance, instance_token)
    except Exception as e:
        logger.exception(e)
        raise


def _get_init_script(instance_service_url, instance_token,
                     instance_name, username, init_file_version):
    instance_config = """\
arg = '{
 "atmosphere":{
  "servicename":"instance service",
  "instance_service_url":"%s",
  "server":"%s",
  "token":"%s",
  "name":"%s",
  "userid":"%s",
  "vnc_license":"%s"
 }
}'""" % (instance_service_url, settings.SERVER_URL,
         instance_token, instance_name, username,
         settings.ATMOSPHERE_VNC_LICENSE)

    init_script_file = os.path.join(
        settings.PROJECT_ROOT,
        "init_files/%s/atmo-initer.rb" % init_file_version)
    with open(init_script_file,'r') as the_file:
        init_script_contents = the_file.read()
    init_script_contents += instance_config + "\nmain(arg)"
    return init_script_contents


