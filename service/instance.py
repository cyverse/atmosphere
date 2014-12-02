import os.path
import time
import uuid

from django.utils.timezone import datetime
from djcelery.app import app

from threepio import logger, status_logger

from rtwo.provider import AWSProvider, AWSUSEastProvider,\
    AWSUSWestProvider, EucaProvider,\
    OSProvider, OSValhallaProvider
from rtwo.driver import OSDriver

from core.models.identity import Identity as CoreIdentity
from core.models.instance import convert_esh_instance
from core.models.size import convert_esh_size
from core.models.provider import AccountProvider, Provider

from api import get_esh_driver

from atmosphere import settings
from atmosphere.settings import secrets
from service.quota import check_over_quota
from service.allocation import check_over_allocation
from service.exceptions import OverAllocationError, OverQuotaError,\
    SizeNotAvailable, HypervisorCapacityError, SecurityGroupNotCreated,\
    VolumeAttachConflict
from service.accounts.openstack import AccountDriver as OSAccountDriver
                
def reboot_instance(esh_driver, esh_instance, reboot_type="SOFT"):
    """
    Default to a soft reboot, but allow option for hard reboot.
    """
    #NOTE: We need to check the quota as if the instance were rebooting,
    #      Because in some cases, a reboot is required to get out of the
    #      suspended state..
    check_quota(user.username, identity_id, size, resuming=True)
    esh_driver.reboot_instance(esh_instance, reboot_type=reboot_type)
    #reboots take very little time..
    redeploy_init(esh_driver, esh_instance, countdown=5)

def resize_instance(esh_driver, esh_instance, size_alias,
                    provider_id, identity_id, user):
    size = esh_driver.get_size(size_alias)
    redeploy_task = resize_and_redeploy(esh_driver, esh_instance, identity_id)
    esh_driver.resize_instance(esh_instance, size)
    redeploy_task.apply_async()
    #Write build state for new size
    update_status(esh_driver, esh_instance.id, provider_id, identity_id, user)

def confirm_resize(esh_driver, esh_instance, provider_id, identity_id, user):
    esh_driver.confirm_resize_instance(esh_instance)
    #Double-Check we are counting on new size
    update_status(esh_driver, esh_instance.id, provider_id, identity_id, user)

# Networking specific
def remove_ips(esh_driver, esh_instance, update_meta=True):
    """
    Returns: (floating_removed, fixed_removed)
    """
    network_manager = esh_driver._connection.get_network_manager()
    #Delete the Floating IP
    result = network_manager.disassociate_floating_ip(esh_instance.id)
    logger.info("Removed Floating IP for Instance %s - Result:%s"
                % (esh_instance.id, result))
    if update_meta:
        update_instance_metadata(esh_driver, esh_instance,
                                 data={'public-ip': '',
                                       'public-hostname':''},
                                 replace=False)
    #Fixed
    instance_ports = network_manager.list_ports(device_id=esh_instance.id)
    if instance_ports:
        fixed_ip_port = instance_ports[0]
        fixed_ips = fixed_ip_port.get('fixed_ips',[])
        if fixed_ips:
            fixed_ip = fixed_ips[0]['ip_address']
            result = esh_driver._connection.ex_remove_fixed_ip(esh_instance, fixed_ip)
            logger.info("Removed Fixed IP %s - Result:%s" % (fixed_ip, result))
        return (True, True)
    return (True, False)

def detach_port(esh_driver, esh_instance):
    instance_ports = network_manager.list_ports(device_id=esh_instance.id)
    if instance_ports:
        fixed_ip_port = instance_ports[0]
        result = esh_driver._connection.ex_detach_interface(
                esh_instance.id, fixed_ip_port['id'])
        logger.info("Detached Port: %s - Result:%s" % (fixed_ip_port, result))
    return result

def remove_network(esh_driver, identity_id):
    from service.tasks.driver import remove_empty_network
    remove_empty_network.s(esh_driver.__class__, esh_driver.provider,
                           esh_driver.identity, identity_id,
                           remove_network=False).apply_async(countdown=20)


def restore_network(esh_driver, esh_instance, identity_id):
    core_identity = CoreIdentity.objects.get(id=identity_id)
    network = network_init(core_identity)
    return network

def restore_instance_port(esh_driver, esh_instance):
    """
    This can be ignored when we move to vxlan
    """
    try:
        import libvirt
    except ImportError:
        raise Exception(
            "Cannot restore instance port without libvirt. To Install:"
            " apt-get install python-libvirt\n"
            " cp /usr/lib/python2.7/dist-packages/*libvirt* "
            "/virtualenv/lib/python2.7/site-packages\n")
    conn = libvirt.openReadOnly()

def _extract_network_metadata(network_manager, esh_instance, node_network):
    try:
        network_name = node_network.keys()[0]
        network = network_manager.find_network(network_name)
        node_network = esh_instance.extra.get('addresses')
        network_id = network[0]['id']
        return network_id
    except (IndexError, KeyError) as e:
        logger.warn(
            "Non-standard 'addresses' metadata. "
            "Cannot extract network_id" % esh_instance)
        return None

def _get_network_id(esh_driver, esh_instance):
    """
    For a given instance, retrieve the network-name and 
    convert it to a network-id
    """
    network_id = None
    network_manager = esh_driver._connection.get_network_manager()

    #Get network name from fixed IP metadata 'addresses'
    node_network = esh_instance.extra.get('addresses')
    if node_network:
        network_id = _extract_network_metadata(network_manager, esh_instance, node_network)
    if not network_id:
        tenant_nets = network_manager.tenant_networks()
        if tenant_nets:
            network_id = tenant_nets[0]["id"]
    if not network_id:
        raise Exception("NetworkManager Could not determine the network"
                        "for node %s" % esh_instance)
    return network_id


def resize_and_redeploy(esh_driver, esh_instance, core_identity_id):
    """
    Use this function to kick off the async task when you ONLY want to deploy
    (No add fixed, No add floating)
    """
    from service.tasks.driver import deploy_init_to, deploy_script
    from service.tasks.driver import wait_for_instance, complete_resize
    from service.deploy import deploy_test
    touch_script = deploy_test()
    core_identity = CoreIdentity.objects.get(id=core_identity_id)

    task_one = wait_for_instance.s(
            esh_instance.id, esh_driver.__class__, esh_driver.provider,
            esh_driver.identity, "verify_resize")
    task_two = deploy_script.si(
            esh_driver.__class__, esh_driver.provider,
            esh_driver.identity, esh_instance.id, touch_script)
    task_three = complete_resize.si(
            esh_driver.__class__, esh_driver.provider,
            esh_driver.identity, esh_instance.id,
            core_identity.provider.id, core_identity.id, core_identity.created_by)
    task_four = deploy_init_to.si(
            esh_driver.__class__, esh_driver.provider,
            esh_driver.identity, esh_instance.id,
            redeploy=True)
    #Link em all together!
    task_one.link(task_two)
    task_two.link(task_three)
    task_three.link(task_four)
    return task_one


def redeploy_init(esh_driver, esh_instance, countdown=None):
    """
    Use this function to kick off the async task when you ONLY want to deploy
    (No add fixed, No add floating)
    """
    from service.tasks.driver import deploy_init_to
    logger.info("Add floating IP and Deploy")
    deploy_init_to.s(esh_driver.__class__, esh_driver.provider,
                     esh_driver.identity, esh_instance.id,
                     redeploy=True).apply_async(countdown=countdown)


def restore_ip_chain(esh_driver, esh_instance, redeploy=False,
        core_identity_id=None):
    """
    Returns: a task, chained together
    task chain: wait_for("active") --> AddFixed --> AddFloating
    --> reDeploy
    start with: task.apply_async()
    """
    from service.tasks.driver import \
            wait_for_instance, add_fixed_ip, add_floating_ip, deploy_init_to
    init_task = wait_for_instance.s(
            esh_instance.id, esh_driver.__class__, esh_driver.provider,
            esh_driver.identity, "active",
            #TODO: DELETEME below.
            no_tasks=True)
    #Step 1: Add fixed
    fixed_ip_task = add_fixed_ip.si(
            esh_driver.__class__, esh_driver.provider,
            esh_driver.identity, esh_instance.id, core_identity_id)
    init_task.link(fixed_ip_task)
    #Add float and re-deploy OR just add floating IP...
    if redeploy:
        deploy_task = deploy_init_to.si(esh_driver.__class__, esh_driver.provider,
                     esh_driver.identity, esh_instance.id,
                     redeploy=True)
        fixed_ip_task.link(deploy_task)
    else:
        logger.info("Skip deployment, Add floating IP only")
        floating_ip_task = add_floating_ip.si(esh_driver.__class__, esh_driver.provider,
                          esh_driver.identity,
                          esh_instance.id)
        fixed_ip_task.link(floating_ip_task)
    return init_task


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


def start_instance(esh_driver, esh_instance,
                    provider_id, identity_id, user,
                   restore_ip=True, update_meta=True):
    """

    raise OverQuotaError, OverAllocationError, InvalidCredsError
    """
    from service.tasks.driver import update_metadata
    #Don't check capacity because.. I think.. its already being counted.
    #admin_capacity_check(provider_id, esh_instance.id)
    if restore_ip:
        restore_network(esh_driver, esh_instance, identity_id)
        deploy_task = restore_ip_chain(esh_driver, esh_instance, redeploy=True)

    needs_fixing = esh_instance.extra['metadata'].get('iplant_suspend_fix')
    logger.info("Instance %s needs to hard reboot instead of start" %
            esh_instance.id)
    if needs_fixing:
        return _repair_instance_networking(esh_driver, esh_instance, provider_id, identity_id)

    esh_driver.start_instance(esh_instance)
    if restore_ip:
        deploy_task.apply_async(countdown=10)
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

def admin_capacity_check(provider_id, instance_id):
    from service.driver import get_admin_driver
    from core.models import Provider
    p = Provider.objects.get(id=provider_id)
    admin_driver = get_admin_driver(p)
    instance = admin_driver.get_instance(instance_id)
    if not instance:
        logger.warn("ERROR - Could not find instance id=%s"
                    % (instance_id,))
        return
    hypervisor_hostname = instance.extra['object']\
            .get('OS-EXT-SRV-ATTR:hypervisor_hostname')
    if not hypervisor_hostname:
        logger.warn("ERROR - Server Attribute hypervisor_hostname missing!"
                    "Assumed to be under capacity")
        return
    hypervisor_stats = admin_driver._connection.ex_detail_hypervisor_node(
            hypervisor_hostname)
    return test_capacity(hypervisor_hostname, instance, hypervisor_stats)

def test_capacity(hypervisor_hostname, instance, hypervisor_stats):
    """
    Test that the hypervisor has the capacity to bring an inactive instance
    back online on the compute node
    """
    #CPU tests first (Most likely bottleneck)
    cpu_total = hypervisor_stats['vcpus']
    cpu_used = hypervisor_stats['vcpus_used']
    cpu_needed = instance.size.cpu
    log_str = "Resource:%s Used:%s Additional:%s Total:%s"\
            % ("cpu", cpu_used, cpu_needed, cpu_total)
    logger.debug(log_str)
    if cpu_used + cpu_needed > cpu_total:
        raise HypervisorCapacityError(hypervisor_hostname, "Hypervisor is over-capacity. %s" % log_str)

    # ALL MEMORY VALUES IN MB
    mem_total = hypervisor_stats['memory_mb']
    mem_used = hypervisor_stats['memory_mb_used']
    mem_needed = instance.size.ram
    log_str = "Resource:%s Used:%s Additional:%s Total:%s"\
            % ("mem", mem_used, mem_needed, mem_total)
    logger.debug(log_str)
    if mem_used + mem_needed > mem_total:
        raise HypervisorCapacityError(hypervisor_hostname, "Hypervisor is over-capacity. %s" % log_str)

    # ALL DISK VALUES IN GB
    disk_total = hypervisor_stats['local_gb']
    disk_used = hypervisor_stats['local_gb_used']
    disk_needed = instance.size.disk + instance.size.ephemeral
    log_str = "Resource:%s Used:%s Additional:%s Total:%s"\
            % ("disk", disk_used, disk_needed, disk_total)
    if disk_used + disk_needed > disk_total:
        raise HypervisorCapacityError(hypervisor_hostname, "Hypervisor is over-capacity. %s" % log_str)


def resume_instance(esh_driver, esh_instance,
                    provider_id, identity_id,
                    user, restore_ip=True,
                    update_meta=True):
    """

    raise OverQuotaError, OverAllocationError, InvalidCredsError
    """
    from service.tasks.driver import update_metadata, _update_status_log
    _update_status_log(esh_instance, "Resuming Instance")
    size = esh_driver.get_size(esh_instance.size.id)
    check_quota(user.username, identity_id, size, resuming=True)
    #admin_capacity_check(provider_id, esh_instance.id)
    if restore_ip:
        restore_network(esh_driver, esh_instance, identity_id)
        #restore_instance_port(esh_driver, esh_instance)
        deploy_task = restore_ip_chain(esh_driver, esh_instance, redeploy=True,
                #NOTE: after removing FIXME, This parameter can be removed as well
                core_identity_id=identity_id)
    #FIXME: These three lines are necessary to repair our last network outage.
    # At some point, we should re-evaluate when it is safe to remove
    needs_fixing = esh_instance.extra['metadata'].get('iplant_suspend_fix')
    if needs_fixing:
        return _repair_instance_networking(esh_driver, esh_instance, provider_id, identity_id)

    esh_driver.resume_instance(esh_instance)
    if restore_ip:
        deploy_task.apply_async(countdown=10)

def admin_get_instance(esh_driver, instance_id):
    instance_list = esh_driver.list_all_instances()
    esh_instance = [instance for instance in instance_list if
                    instance.id == instance_id]
    if not esh_instance:
        return None
    return esh_instance[0]

def update_status(esh_driver, instance_id, provider_id, identity_id, user):
    """
    All that this method really does is:
    * Query for the instance
    * call 'convert_esh_instance'
    Converting the instance internally updates the status history..
    But it makes more sense to call this function in the code..
    """
    #Grab a new copy of the instance

    if AccountProvider.objects.filter(identity__id=identity_id):
        esh_instance = admin_get_instance(esh_driver, instance_id)
    else:
        esh_instance = esh_driver.get_instance(instance_id)
    if not esh_instance:
        return None
    #Convert & Update based on new status change
    core_instance = convert_esh_instance(esh_driver,
                                         esh_instance,
                                         provider_id,
                                         identity_id,
                                         user)


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
    _check_volume_attachment(esh_driver, instance)
    if isinstance(esh_driver, OSDriver):
        #Openstack: Remove floating IP first
        try:
            esh_driver._connection.ex_disassociate_floating_ip(instance)
        except Exception as exc:
            if 'floating ip not found' not in exc.message:
                raise
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
    now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if machine_alias:
        alias = "machine,%s" % machine_alias
    elif 'volume_alias' in kwargs:
        alias = "boot_volume,%s" % kwargs['volume_alias']
    else:
        raise Exception("Not enough data to launch: "
                        "volume_alias/machine_alias is missing")
    status_logger.debug("%s,%s,%s,%s,%s,%s"
                 % (now_time, user, "No Instance", alias, size_alias,
                    "Request Received"))
    core_identity = CoreIdentity.objects.get(id=identity_id)

    esh_driver = get_esh_driver(core_identity, user)
    size = esh_driver.get_size(size_alias)

    #May raise SizeNotAvailable
    check_size(size, provider_id)

    #May raise OverQuotaError or OverAllocationError
    check_quota(user.username, identity_id, size)

    #May raise InvalidCredsError, SecurityGroupNotCreated
    (esh_instance, token, password) = launch_esh_instance(esh_driver,
            machine_alias, size_alias, core_identity, **kwargs)
    #Convert esh --> core
    core_instance = convert_esh_instance(
        esh_driver, esh_instance, provider_id, identity_id,
        user, token, password)
    esh_size = esh_driver.get_size(esh_instance.size.id)
    core_size = convert_esh_size(esh_size, provider_id)
    core_instance.update_history(
        core_instance.esh.extra['status'],
        core_size,
        #3rd arg is task OR tmp_status
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
    if over_quota and settings.ENFORCING:
        raise OverQuotaError(resource, requested, used, allowed)
    (over_allocation, time_diff) =\
        check_over_allocation(username,
                              identity_id,
                              time_period=settings.FIXED_WINDOW)
    if over_allocation and settings.ENFORCING:
        raise OverAllocationError(time_diff)


def security_group_init(core_identity, max_attempts = 3):
    os_driver = OSAccountDriver(core_identity.provider)
    creds = core_identity.get_credentials()
    #TODO: Remove kludge when openstack connections can be
    #Deemed reliable. Otherwise generalize this pattern so it
    #can be arbitrarilly applied to any call that is deemed 'unstable'.
    # -Steve
    attempt = 0
    while attempt < max_attempts:
        attempt += 1
        security_group = os_driver.init_security_group(
            creds['key'], creds['secret'],
            creds['ex_tenant_name'], creds['ex_tenant_name'],
            os_driver.MASTER_RULES_LIST)
        if security_group:
            return security_group
        time.sleep(2**attempt)
    raise SecurityGroupNotCreated()


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
    lc_network = _to_lc_network(os_driver.admin_driver, network, subnet)
    return lc_network


def _to_lc_network(driver, network, subnet):
    from libcloud.compute.drivers.openstack import OpenStackNetwork
    lc_network = OpenStackNetwork(
            network['id'],
            network['name'],
            subnet['cidr'],
            driver,
            {"network":network,
             "subnet": subnet})
    return lc_network


def launch_esh_instance(driver, machine_alias, size_alias, core_identity,
        name=None, username=None, using_admin=False,
        *args, **kwargs):

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
            if not using_admin:
                security_group_init(core_identity)
            network = network_init(core_identity)
            keypair_init(core_identity)
            credentials = core_identity.get_credentials()
            tenant_name = credentials.get('ex_tenant_name')
            ex_metadata = {'tmp_status': 'initializing',
                           'tenant_name': tenant_name,
                           'creator': '%s' % username}
            ex_keyname = settings.ATMOSPHERE_KEYPAIR_NAME
            logger.debug("OS driver.create_instance kwargs: %s" % kwargs)
            esh_instance = driver.create_instance(name=name, image=machine,
                                                  size=size,
                                                  token=instance_token,
                                                  ex_metadata=ex_metadata,
                                                  ex_keyname=ex_keyname,
                                                  networks=[network],
                                                  deploy=True, **kwargs)
            #Used for testing.. Eager ignores countdown
            if app.conf.CELERY_ALWAYS_EAGER:
                logger.debug("Eager Task, wait 1 minute")
                time.sleep(1*60)
            # call async task to deploy to instance.
            task.deploy_init_task(driver, esh_instance, username,
                                  instance_password, instance_token)
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
    if not esh_instance:
        return {}
    instance_id = esh_instance.id

    if not hasattr(esh_driver._connection, 'ex_write_metadata'):
        logger.warn("EshDriver %s does not have function 'ex_write_metadata'"
                    % esh_driver._connection.__class__)
        return {}
    if esh_instance.extra['status'] == 'build':
        raise Exception("Metadata cannot be applied while EshInstance %s is in"
                        " the build state." % (esh_instance,))
    # ASSERT: We are ready to update the metadata
    if data.get('name'):
        esh_driver._connection.ex_set_server_name(esh_instance, data['name'])
    try:
        return esh_driver._connection.ex_write_metadata(esh_instance, data,
                replace_metadata=replace)
    except Exception, e:
        logger.exception("Error updating the metadata")
        if 'incapable of performing the request' in e.message:
            return {}
        else:
            raise


def _create_and_attach_port(provider, driver, instance, core_identity):
    accounts = OSAccountDriver(core_identity.provider)
    tenant_id = instance.extra['tenantId']
    network_resources = accounts.network_manager.find_tenant_resources(tenant_id)
    network = network_resources['networks']
    if not network:
        network, subnet = accounts.create_network(core_identity)
    else:
        network = network[0]
        subnet = network_resources['subnets'][0]
    #new_fixed_ip = _get_next_fixed_ip(network_resources['ports'])
    #admin = accounts.admin_driver
    #port = accounts.network_manager.create_port(
    #    instance.id, network['id'], subnet['id'], new_fixed_ip, tenant_id)
    attached_intf = driver._connection.ex_attach_interface(instance.id, network['id'])
    return attached_intf
   
def _get_next_fixed_ip(ports):
    """
    Expects the output from user-specific neutron port-list. will determine the
    next available fixed IP by 'counting' the highest allocated IP address and
    adding one to it.
    """
    try:
        from iptools.ipv4 import ip2long, long2ip
    except ImportError:
        raise Exception("For this script, we need iptools. pip install iptools")
    max_ip = -1
    for port in ports:
        fixed_ip = port['fixed_ips']
        if not fixed_ip:
            continue
        fixed_ip = fixed_ip[0]['ip_address']
        max_ip = max(max_ip, ip2long(fixed_ip))
    if max_ip <= 0:
        raise Exception("Next IP address could not be determined"
                        " (You have no existing Fixed IPs!)")
    new_fixed_ip = long2ip(max_ip + 1)
    return new_fixed_ip

def _repair_instance_networking(esh_driver, esh_instance, provider_id, identity_id):
    from service.tasks.driver import \
            add_floating_ip, wait_for_instance, \
            deploy_init_to, deploy_failed, update_metadata
    logger.info("Instance %s needs to create and attach port instead"
                % esh_instance.id)
    core_identity = CoreIdentity.objects.get(id=identity_id)
    provider = Provider.objects.get(id=provider_id)
    logger.info("Attaching interface manually, Instance %s" %
                esh_instance.id)
    attached_intf = _create_and_attach_port(provider, esh_driver, esh_instance,
                core_identity)
    logger.info("Attached Interface: %s" % attached_intf)
    logger.info("Adding floating IP manually, Instance %s" %
                esh_instance.id)
    add_floating_ip(esh_driver.__class__, esh_driver.provider,
                    esh_driver.identity, esh_instance.id)
    logger.info("Instance %s needs to hard reboot instead of resume" %
                esh_instance.id)
    esh_driver.reboot_instance(esh_instance,'HARD')

    #Custom task-chain.. Wait for active then redeploy scripts
    #(Adding IP is done).. Then remove metadata
    init_task = wait_for_instance.s(
            esh_instance.id, esh_driver.__class__, esh_driver.provider,
            esh_driver.identity, "active")

    deploy_task = deploy_init_to.si(esh_driver.__class__, esh_driver.provider,
                     esh_driver.identity, esh_instance.id,
                     redeploy=True)
    deploy_task.link_error(
        deploy_failed.s(esh_driver.__class__, esh_driver.provider,
            esh_driver.identity, esh_instance.id))

    final_update = esh_instance.extra['metadata']
    final_update.pop('tmp_status')
    final_update.pop('iplant_suspend_fix')
    remove_status_task = update_metadata.si(
            esh_driver.__class__, esh_driver.provider, esh_driver.identity,
            esh_instance.id, final_update, replace_metadata=True)
    deploy_task.link(remove_status_task)

    #Attempt to redeploy after the restart..
    init_task.link(deploy_task)
    init_task.apply_async()
    return


def _check_volume_attachment(driver, instance):
    volumes = driver.list_volumes()
    for vol in volumes:
        attachment_set = vol.extra.get('attachments',[])
        if not attachment_set:
            continue
        for attachment in attachment_set:
            if instance.alias == attachment['serverId']:
                raise VolumeAttachConflict(instance.alias, vol.alias)
    return False
