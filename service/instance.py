import uuid
import time
import os.path
from djcelery.app import app

from rtwo.provider import AWSProvider, AWSUSEastProvider,\
    AWSUSWestProvider, EucaProvider,\
    OSProvider, OSValhallaProvider
from rtwo.driver import OSDriver
from threepio import logger

from core.models.identity import Identity as CoreIdentity
from core.models.instance import convert_esh_instance
from core.models.size import convert_esh_size
from core.models.provider import AccountProvider

from atmosphere import settings
from atmosphere.settings import secrets

from api import get_esh_driver

from service.quota import check_over_quota
from service.allocation import check_over_allocation
from service.exceptions import OverAllocationError, OverQuotaError,\
    SizeNotAvailable
from service.accounts.openstack import AccountDriver as OSAccountDriver


# Networking specific
def remove_ips(esh_driver, esh_instance):
    network_manager = esh_driver._connection.get_network_manager()
    network_manager.disassociate_floating_ip(esh_instance.id)
    instance_ports = network_manager.list_ports(device_id=esh_instance.id)
    if instance_ports:
        fixed_ips = instance_ports[0].get('fixed_ips',[])
        if fixed_ips:
            fixed_ip = fixed_ips[0]['ip_address']
            esh_driver._connection.ex_remove_fixed_ip(esh_instance, fixed_ip)

def remove_network(esh_driver, identity_id):
    from service.tasks.driver import remove_empty_network
    remove_empty_network.s(esh_driver.__class__, esh_driver.provider,
                           esh_driver.identity, identity_id,
                           remove_network=False).apply_async(countdown=20)


def restore_network(esh_driver, esh_instance, identity_id):
    core_identity = CoreIdentity.objects.get(id=identity_id)
    (network, subnet) = network_init(core_identity)
    return network, subnet

def restore_ips(esh_driver, esh_instance):
    from service.tasks.driver import add_floating_ip
    node_network = esh_instance.extra.get('addresses')
    if not node_network:
        raise Exception("Could not determine the network for node %s"
                        % node)
    try:
        network_name = node_network.keys()[0]
    except Exception, e:
        raise Exception("Could not determine network name for node %s"
                        % node)

    try:
        network_manager = esh_driver._connection.get_network_manager()
        network = network_manager.find_network(network_name)
        if not network:
            raise Exception("NetworkManager Could not determine the network"
                        "for node %s" % node)
        network_id = network[0]['id']
    except Exception, e:
        raise

    esh_driver._connection.ex_add_fixed_ip(esh_instance, network_id)
    add_floating_ip.s(esh_driver.__class__, esh_driver.provider,
                      esh_driver.identity,
                      esh_instance.id).apply_async(countdown=10)


#Instance specific
def stop_instance(esh_driver, esh_instance, provider_id, identity_id, user,
                  reclaim_ip=True):
    """

    raise OverQuotaError, OverAllocationError, InvalidCredsError
    """
    if reclaim_ip:
        remove_ips(esh_driver, esh_instance)
    stopped = esh_driver.stop_instance(esh_instance)
    if reclaim_ip:
        remove_network(esh_driver, identity_id)
    update_status(esh_driver, esh_instance.id, provider_id, identity_id, user)


def start_instance(esh_driver, esh_instance, provider_id, identity_id, user,
                   restore_ip=True, update_meta=True):
    """

    raise OverQuotaError, OverAllocationError, InvalidCredsError
    """
    from service.tasks.driver import update_metadata
    if restore_ip:
        restore_network(esh_driver, esh_instance, identity_id)
    if update_meta:
        update_instance_metadata(esh_driver, esh_instance,
                                 data={'tmp_status': 'networking'},
                                 replace=False)
    esh_driver.start_instance(esh_instance)
    if restore_ip:
        restore_ips(esh_driver, esh_instance)
    if update_meta:
        #Run this task only when instance moves from suspended --> active
        update_metadata.s(
            esh_driver.__class__, esh_driver.provider, esh_driver.identity,
            esh_instance.id, {'tmp_status': ''}).apply_async(countdown=30)
    update_status(esh_driver, esh_instance.id, provider_id, identity_id, user)


def suspend_instance(esh_driver, esh_instance,
                     provider_id, identity_id,
                     user, reclaim_ip=True):
    """

    raise OverQuotaError, OverAllocationError, InvalidCredsError
    """
    if reclaim_ip:
        remove_ips(esh_driver, esh_instance)
    suspended = esh_driver.suspend_instance(esh_instance)
    if reclaim_ip:
        remove_network(esh_driver, identity_id)
    update_status(esh_driver, esh_instance.id, provider_id, identity_id, user)
    return suspended


def resume_instance(esh_driver, esh_instance,
                    provider_id, identity_id,
                    user, restore_ip=True,
                    update_meta=True):
    """

    raise OverQuotaError, OverAllocationError, InvalidCredsError
    """
    from service.tasks.driver import update_metadata
    check_quota(user.username, identity_id, esh_instance.size, resuming=True)
    if restore_ip:
        restore_network(esh_driver, esh_instance, identity_id)
    if update_meta:
        update_instance_metadata(esh_driver, esh_instance,
                                 data={'tmp_status': 'networking'},
                                 replace=False)
    esh_driver.resume_instance(esh_instance)
    if restore_ip:
        restore_ips(esh_driver, esh_instance)
    if update_meta:
        #Run this task only when instance moves from suspended --> active
        update_metadata.s(
            esh_driver.__class__, esh_driver.provider, esh_driver.identity,
            esh_instance.id, {'tmp_status': ''}).apply_async(countdown=30)
    update_status(esh_driver, esh_instance.id, provider_id, identity_id, user)


def update_status(esh_driver, instance_id, provider_id, identity_id, user):
    #Grab a new copy of the instance
    instance_list_method = esh_driver.list_instances

    if AccountProvider.objects.filter(identity__id=identity_id):
        # Instance list method changes when using the OPENSTACK provider
        instance_list_method = esh_driver.list_all_instances

    try:
        esh_instance_list = instance_list_method()
    except InvalidCredsError:
        return invalid_creds(provider_id, identity_id)

    esh_instance = [instance for instance in esh_instance_list if
                    instance.id == instance_id]
    esh_instance = esh_instance[0]

    #Convert & Update based on new status change
    core_instance = convert_esh_instance(esh_driver,
                                         esh_instance,
                                         provider_id,
                                         identity_id,
                                         user)
    core_instance.update_history(
        core_instance.esh.extra['status'],
        core_instance.esh.extra.get('task'))


def get_core_instances(identity_id):
    identity = CoreIdentity.objects.get(id=identity_id)
    driver = get_esh_driver(identity)
    instances = driver.list_instances()
    core_instances = [convert_esh_instance(driver,
                                           esh_instance,
                                           identity.provider.id,
                                           identity.id,
                                           identity.created_by)
                      for esh_instance in instances]
    return core_instances


def destroy_instance(identity_id, instance_alias):
    core_identity = CoreIdentity.objects.get(id=identity_id)
    esh_driver = get_esh_driver(core_identity)
    instance = esh_driver.get_instance(instance_alias)
    #Bail if instance doesnt exist
    if not instance:
        return None
    if isinstance(esh_driver, OSDriver):
        #Openstack: Remove floating IP first
        esh_driver._connection.ex_disassociate_floating_ip(instance)
    node_destroyed = esh_driver._connection.destroy_node(instance)
    return node_destroyed


def launch_instance(user, provider_id, identity_id,
                    size_alias, machine_alias, **kwargs):
    """
    Required arguments will launch the instance, extras will do
    provider-specific modifications.

    Test the quota, Launch the instance,
    creates a core repr and updates status.

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
    (esh_instance, token, password) = launch_esh_instance(esh_driver, machine_alias,
                                                size_alias, core_identity,
                                                **kwargs)
    #Convert esh --> core
    core_instance = convert_esh_instance(
        esh_driver, esh_instance, provider_id, identity_id,
        user, token, password)
    core_instance.update_history(
        core_instance.esh.extra['status'],
        #2nd arg is task OR tmp_status
        core_instance.esh.extra.get('task') or
        core_instance.esh.extra.get('metadata', {}).get('tmp_status'),
        first_update=True)

    return core_instance


def check_size(esh_size, provider_id):
    try:
        if not convert_esh_size(esh_size, provider_id).active():
            raise SizeNotAvailable()
    except:
        raise SizeNotAvailable()


def check_quota(username, identity_id, esh_size, resuming=False):
    (over_quota, resource,
     requested, used, allowed) = check_over_quota(username,
                                                  identity_id,
                                                  esh_size, resuming=resuming)
    if over_quota:
        raise OverQuotaError(resource, requested, used, allowed)

    (over_allocation, time_diff) = check_over_allocation(username,
                                                         identity_id)
    if over_allocation:
        raise OverAllocationError(time_diff)


def security_group_init(core_identity):
    os_driver = OSAccountDriver(core_identity.provider)
    creds = core_identity.get_credentials()
    security_group = os_driver.init_security_group(
        creds['key'], creds['secret'],
        creds['ex_tenant_name'], creds['ex_tenant_name'],
        os_driver.MASTER_RULES_LIST)
    return security_group


def keypair_init(core_identity):
    os_driver = OSAccountDriver(core_identity.provider)
    creds = core_identity.get_credentials()
    with open(settings.ATMOSPHERE_KEYPAIR_FILE, 'r') as pub_key_file:
        public_key = pub_key_file.read()
    keypair, created = os_driver.get_or_create_keypair(
        creds['key'], creds['secret'], creds['ex_tenant_name'],
        settings.ATMOSPHERE_KEYPAIR_NAME, public_key)
    if created:
        logger.info("Created keypair for %s" % creds['key'])
    return keypair


def network_init(core_identity):
    provider_creds = core_identity.provider.get_credentials()
    if 'router_name' not in provider_creds.keys():
        logger.warn("ProviderCredential 'router_name' missing:"
                    "cannot create virtual network")
        return
    os_driver = OSAccountDriver(core_identity.provider)
    (network, subnet) = os_driver.create_network(core_identity)
    return (network, subnet)


def launch_esh_instance(driver, machine_alias, size_alias, core_identity,
                        name=None, username=None, *args, **kwargs):
    """
    TODO: Remove extras, pass as kwarg_dict instead

    return the esh_instance & instance token
    """
    from service import task
    try:
        #create a reference to this attempted instance launch.
        instance_token = str(uuid.uuid4())
        #create a unique one-time password for instance root user
        instance_password = str(uuid.uuid4())

        #TODO: Mock these for faster launch performance
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
            init_file_version = kwargs.get('init_file', "v1")
            # Remove quotes -- Single && Double
            name = name.replace('"', '').replace("'", "")
            userdata_contents = _get_init_script(instance_service_url,
                                                 instance_token,
                                                 instance_password,
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
            security_group_init(core_identity)
            network_init(core_identity)
            keypair_init(core_identity)
            ex_metadata = {'tmp_status': 'initializing',
                           'creator': '%s' % username}
            ex_keyname = settings.ATMOSPHERE_KEYPAIR_NAME
            logger.debug("OS driver.create_instance kwargs: %s" % kwargs)
            esh_instance = driver.create_instance(name=name, image=machine,
                                                  size=size,
                                                  token=instance_token,
                                                  ex_metadata=ex_metadata,
                                                  ex_keyname=ex_keyname,
                                                  deploy=True, **kwargs)
            #Used for testing.. Eager ignores countdown
            if app.conf.CELERY_ALWAYS_EAGER:
                time.sleep(4*60)
            # call async task to deploy to instance.
            task.deploy_init_task(driver, esh_instance, instance_password)
        elif isinstance(driver.provider, AWSProvider):
            #TODO:Extra stuff needed for AWS provider here
            esh_instance = driver.deploy_instance(name=name, image=machine,
                                                  size=size, deploy=True,
                                                  token=instance_token,
                                                  **kwargs)
        else:
            raise Exception("Unable to launch with this provider.")
        return (esh_instance, instance_token, instance_password)
    except Exception as e:
        logger.exception(e)
        raise


def _get_init_script(instance_service_url, instance_token, instance_password,
                     instance_name, username, init_file_version="v1"):
    instance_config = """\
arg = '{
 "atmosphere":{
  "servicename":"instance service",
  "instance_service_url":"%s",
  "server":"%s",
  "token":"%s",
  "name":"%s",
  "userid":"%s",
  "vnc_license":"%s",
  "root_password":"%s"
 }
}'""" % (instance_service_url, settings.SERVER_URL,
         instance_token, instance_name, username,
         secrets.ATMOSPHERE_VNC_LICENSE, instance_password)

    init_script_file = os.path.join(
        settings.PROJECT_ROOT,
        "init_files/%s/atmo-initer.rb" % init_file_version)
    with open(init_script_file, 'r') as the_file:
        init_script_contents = the_file.read()
    init_script_contents += instance_config + "\nmain(arg)"
    return init_script_contents

def update_instance_metadata(esh_driver, esh_instance, data={}, replace=True):
    """
    NOTE: This will NOT WORK for TAGS until openstack
    allows JSONArrays as values for metadata!
    """
    wait_time = 1
    instance_id = esh_instance.id

    if not hasattr(esh_driver._connection, 'ex_set_metadata'):
        logger.warn("EshDriver %s does not have function 'ex_set_metadata'"
                    % esh_driver._connection.__class__)
        return {}
    if esh_instance.extra['status'] == 'build':
        raise Exception("Metadata cannot be applied while EshInstance %s is in"
                        " the build state." % (esh_instance,))
    # ASSERT: We are ready to update the metadata
    if data.get('name'):
        esh_driver._connection.ex_set_server_name(esh_instance, data['name'])
    try:
        return esh_driver._connection.ex_set_metadata(esh_instance, data,
                replace_metadata=replace)
    except Exception, e:
        logger.exception("Error updating the metadata")
        if 'incapable of performing the request' in e.message:
            return {}
        else:
            raise

