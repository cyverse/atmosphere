import os.path
import time
import uuid

from django.utils.text import slugify
from django.utils.timezone import datetime
from djcelery.app import app

from threepio import logger, status_logger

from rtwo.provider import AWSProvider, AWSUSEastProvider,\
    AWSUSWestProvider, EucaProvider,\
    OSProvider, OSValhallaProvider
from rtwo.driver import OSDriver
from rtwo.machine import Machine
from rtwo.size import MockSize
from rtwo.volume import Volume


from core.query import only_current
from core.models.abstract import InstanceSource
from core.models.application import Application
from core.models.identity import Identity as CoreIdentity
from core.models.instance import convert_esh_instance
from core.models.size import convert_esh_size
from core.models.machine import ProviderMachine
from core.models.provider import AccountProvider, Provider

from atmosphere import settings
from atmosphere.settings import secrets

from service.cache import get_cached_driver, invalidate_cached_instances
from service.driver import _retrieve_source
from service.quota import check_over_quota
from service.monitoring import check_over_allocation
from service.exceptions import OverAllocationError, OverQuotaError,\
    SizeNotAvailable, HypervisorCapacityError, SecurityGroupNotCreated,\
    VolumeAttachConflict, UnderThresholdError
from service.accounts.openstack import AccountDriver as OSAccountDriver

def _get_size(esh_driver, esh_instance):
    if type(esh_instance.size) == MockSize:
        size = esh_driver.get_size(esh_instance.size.id)
    else:
        size = esh_instance.size
    return size


def reboot_instance(esh_driver, esh_instance, identity_uuid, user, reboot_type="SOFT"):
    """
    Default to a soft reboot, but allow option for hard reboot.
    """
    #NOTE: We need to check the quota as if the instance were rebooting,
    #      Because in some cases, a reboot is required to get out of the
    #      suspended state..
    size = _get_size(esh_driver, esh_instance)
    check_quota(user.username, identity_uuid, size, resuming=True)
    esh_driver.reboot_instance(esh_instance, reboot_type=reboot_type)
    #reboots take very little time..
    redeploy_init(esh_driver, esh_instance, countdown=5)


def resize_instance(esh_driver, esh_instance, size_alias,
                    provider_uuid, identity_uuid, user):
    size = esh_driver.get_size(size_alias)
    redeploy_task = resize_and_redeploy(esh_driver, esh_instance, identity_uuid)
    esh_driver.resize_instance(esh_instance, size)
    redeploy_task.apply_async()
    #Write build state for new size
    update_status(esh_driver, esh_instance.id, provider_uuid, identity_uuid, user)


def confirm_resize(esh_driver, esh_instance, provider_uuid, identity_uuid, user):
    esh_driver.confirm_resize_instance(esh_instance)
    #Double-Check we are counting on new size
    update_status(esh_driver, esh_instance.id, provider_uuid, identity_uuid, user)


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

def remove_network(esh_driver, identity_uuid, remove_network=False):
    from service.tasks.driver import remove_empty_network
    remove_empty_network.s(esh_driver.__class__, esh_driver.provider,
                           esh_driver.identity, identity_uuid,
                           remove_network=remove_network).apply_async(countdown=20)


def restore_network(esh_driver, esh_instance, identity_uuid):
    core_identity = CoreIdentity.objects.get(uuid=identity_uuid)
    network = network_init(core_identity)
    return network


def restore_instance_port(esh_driver, esh_instance):
    """
    This can be ignored when we move to vxlan..

    For a given instance, retrieve the network-name and
    convert it to a network-id
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


def resize_and_redeploy(esh_driver, esh_instance, core_identity_uuid):
    """
    Use this function to kick off the async task when you ONLY want to deploy
    (No add fixed, No add floating)
    """
    from service.tasks.driver import deploy_init_to, deploy_script
    from service.tasks.driver import wait_for_instance, complete_resize
    from service.deploy import deploy_test
    touch_script = deploy_test()
    core_identity = CoreIdentity.objects.get(uuid=core_identity_uuid)

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
    #TODO: Add an appropriate link_error and track/handle failures.
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
        core_identity_uuid=None):
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
            esh_driver.identity, esh_instance.id, core_identity_uuid)
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


def stop_instance(esh_driver, esh_instance, provider_uuid, identity_uuid, user,
                  reclaim_ip=True):
    """

    raise OverQuotaError, OverAllocationError, InvalidCredsError
    """
    if reclaim_ip:
        remove_ips(esh_driver, esh_instance)
    stopped = esh_driver.stop_instance(esh_instance)
    if reclaim_ip:
        remove_network(esh_driver, identity_uuid)
    update_status(esh_driver, esh_instance.id, provider_uuid, identity_uuid, user)
    invalidate_cached_instances(
        identity=CoreIdentity.objects.get(uuid=identity_uuid))


def start_instance(esh_driver, esh_instance,
                    provider_uuid, identity_uuid, user,
                   restore_ip=True, update_meta=True):
    """

    raise OverQuotaError, OverAllocationError, InvalidCredsError
    """
    from service.tasks.driver import update_metadata
    #Don't check capacity because.. I think.. its already being counted.
    #admin_capacity_check(provider_uuid, esh_instance.id)
    if restore_ip:
        restore_network(esh_driver, esh_instance, identity_uuid)
        deploy_task = restore_ip_chain(esh_driver, esh_instance, redeploy=True)

    needs_fixing = esh_instance.extra['metadata'].get('iplant_suspend_fix')
    logger.info("Instance %s needs to hard reboot instead of start" %
            esh_instance.id)
    if needs_fixing:
        return _repair_instance_networking(esh_driver, esh_instance, provider_uuid, identity_uuid)

    esh_driver.start_instance(esh_instance)
    if restore_ip:
        deploy_task.apply_async(countdown=10)
    update_status(esh_driver, esh_instance.id, provider_uuid, identity_uuid, user)
    invalidate_cached_instances(identity=CoreIdentity.objects.get(uuid=identity_uuid))


def suspend_instance(esh_driver, esh_instance,
                     provider_uuid, identity_uuid,
                     user, reclaim_ip=True):
    """

    raise OverQuotaError, OverAllocationError, InvalidCredsError
    """
    if reclaim_ip:
        remove_ips(esh_driver, esh_instance)
    suspended = esh_driver.suspend_instance(esh_instance)
    if reclaim_ip:
        remove_network(esh_driver, identity_uuid)
    update_status(esh_driver, esh_instance.id, provider_uuid, identity_uuid, user)
    invalidate_cached_instances(identity=CoreIdentity.objects.get(uuid=identity_uuid))
    return suspended


def admin_capacity_check(provider_uuid, instance_id):
    from service.driver import get_admin_driver
    from core.models import Provider
    p = Provider.objects.get(uuid=provider_uuid)
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
                    provider_uuid, identity_uuid,
                    user, restore_ip=True,
                    update_meta=True):
    """
    raise OverQuotaError, OverAllocationError, InvalidCredsError
    """
    from service.tasks.driver import update_metadata, _update_status_log
    _update_status_log(esh_instance, "Resuming Instance")
    size = _get_size(esh_driver, esh_instance)
    check_quota(user.username, identity_uuid, size, resuming=True)
    #admin_capacity_check(provider_uuid, esh_instance.id)
    if restore_ip:
        restore_network(esh_driver, esh_instance, identity_uuid)
        #restore_instance_port(esh_driver, esh_instance)
        deploy_task = restore_ip_chain(esh_driver, esh_instance, redeploy=True,
                #NOTE: after removing FIXME, This parameter can be removed as well
                core_identity_uuid=identity_uuid)
    #FIXME: These three lines are necessary to repair our last network outage.
    # At some point, we should re-evaluate when it is safe to remove
    needs_fixing = esh_instance.extra['metadata'].get('iplant_suspend_fix')
    if needs_fixing:
        return _repair_instance_networking(esh_driver, esh_instance, provider_uuid, identity_uuid)

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

def update_status(esh_driver, instance_id, provider_uuid, identity_uuid, user):
    """
    All that this method really does is:
    * Query for the instance
    * call 'convert_esh_instance'
    Converting the instance internally updates the status history..
    But it makes more sense to call this function in the code..
    """
    #Grab a new copy of the instance

    if AccountProvider.objects.filter(identity__uuid=identity_uuid):
        esh_instance = admin_get_instance(esh_driver, instance_id)
    else:
        esh_instance = esh_driver.get_instance(instance_id)
    if not esh_instance:
        return None
    #Convert & Update based on new status change
    core_instance = convert_esh_instance(esh_driver,
                                         esh_instance,
                                         provider_uuid,
                                         identity_uuid,
                                         user)


def get_core_instances(identity_uuid):
    identity = CoreIdentity.objects.get(uuid=identity_uuid)
    driver = get_cached_driver(identity=identity)
    instances = driver.list_instances()
    core_instances = [convert_esh_instance(driver,
                                           esh_instance,
                                           identity.provider.uuid,
                                           identity.uuid,
                                           identity.created_by)
                      for esh_instance in instances]
    return core_instances


def destroy_instance(identity_uuid, instance_alias):
    identity = CoreIdentity.objects.get(uuid=identity_uuid)
    esh_driver = get_cached_driver(identity=identity)
    instance = esh_driver.get_instance(instance_alias)
    #Bail if instance doesnt exist
    if not instance:
        return None
    #_check_volume_attachment(esh_driver, instance)
    if isinstance(esh_driver, OSDriver):
        try:
            # Openstack: Remove floating IP first
            esh_driver._connection.ex_disassociate_floating_ip(instance)
        except Exception as exc:
            # Ignore 'safe' errors related to
            # no floating IP
            # or no Volume capabilities.
            if not ("floating ip not found" in exc.message
                    or "422 Unprocessable Entity Floating ip" in exc.message
                    or "500 Internal Server Error" in exc.message):
                raise
    node_destroyed = esh_driver._connection.destroy_node(instance)
    return node_destroyed


def launch_instance(user, provider_uuid, identity_uuid,
                    size_alias, source_alias, **kwargs):
    """
    Initialization point --> launch_*_instance --> ..
    Required arguments will launch the instance, extras will do
    provider-specific modifications.

    1. Test for available Size (on specific driver!)
    2. Test user has Quota/Allocation (on our DB)
    3. Test user is launching appropriate size (Not below Thresholds)
    4. Perform an 'Instance launch' depending on Boot Source
    5. Return CORE Instance with new 'esh' objects attached.
    """
    now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status_logger.debug("%s,%s,%s,%s,%s,%s"
                 % (now_time, user, "No Instance", source_alias, size_alias,
                    "Request Received"))
    identity = CoreIdentity.objects.get(uuid=identity_uuid)
    esh_driver = get_cached_driver(identity=identity)

    #May raise SizeNotAvailable
    size = check_size(esh_driver, size_alias, provider_uuid)

    #May raise OverQuotaError or OverAllocationError
    check_quota(user.username, identity_uuid, size)

    #May raise UnderThresholdError
    check_application_threshold(user.username, identity_uuid, size, source_alias)

    #May raise Exception("Volume/Machine not available")
    boot_source = get_boot_source(user.username, identity_uuid, source_alias)
    if boot_source.is_volume():
        #NOTE: THIS route works when launching an EXISTING volume ONLY
        #      to CREATE a new bootable volume (from an existing volume/image/snapshot)
        #      use service/volume.py 'boot_volume'
        volume = _retrieve_source(esh_driver, boot_source.identifier, "volume")
        core_instance = launch_volume_instance(esh_driver, identity,
                volume, size, **kwargs)
    elif boot_source.is_machine():
        machine = _retrieve_source(esh_driver, boot_source.identifier, "machine")
        core_instance = launch_machine_instance(esh_driver, identity,
                machine, size, **kwargs)
    else:
        raise Exception("Boot source is of an unknown type")
    return core_instance

def boot_volume_instance(
        driver, identity, copy_source, size, name,
        #Depending on copy source, these specific kwargs may/may not be used.
        boot_index=0, shutdown=False, volume_size=None,
        #Other kwargs passed for future needs
        **kwargs):
    """
    boot_volume_instance : return CoreInstance
    """
    kwargs, userdata, network = _pre_launch_instance(driver, identity, size, name, **kwargs)
    kwargs.update(prep_kwargs)
    instance, token, password = _boot_volume(
            driver, identity, copy_source, size,
            name, userdata, network, **kwargs)
    return _complete_launch_instance(driver, identity, instance,
            identity.created_by, token, password)

def launch_volume_instance(driver, identity, volume, size, name, **kwargs):
    kwargs, userdata, network = _pre_launch_instance(driver, identity, size, name, **kwargs)
    kwargs.update(prep_kwargs)
    instance ,token, password = _launch_volume(
            driver, identity, volume, size,
            name, userdata, network, **kwargs)
    return _complete_launch_instance(driver, identity, instance,
           identity.created_by, token, password)

def launch_machine_instance(driver, identity, machine, size, name, **kwargs):
    prep_kwargs,  userdata, network = _pre_launch_instance(driver, identity, size, name, **kwargs)
    kwargs.update(prep_kwargs)
    instance, token, password = _launch_machine(
            driver, identity, machine, size,
            name, userdata, network, **kwargs)
    return _complete_launch_instance(driver, identity, instance,
            identity.created_by, token, password)


def _boot_volume(driver, identity, copy_source, size, name, userdata, network,
                    password=None, token=None, 
                    boot_index=0, shutdown=False, **kwargs):
    image, snapshot, volume = _select_copy_source(copy_source)
    if not isinstance(driver.provider, OSProvider):
        raise ValueError("The Provider: %s can't create bootable volumes"
                         % driver.provider)
    extra_args = _extra_openstack_args(identity)
    kwargs.update(extra_args)
    boot_success, new_instance = driver.boot_volume(
            name=name, image=None, snapshot=None, volume=volume,
            boot_index=boot_index, shutdown=shutdown,
            volume_size=None, size=size, networks=[network],
            ex_admin_pass=password, **kwargs)
    return (new_instance, token, password)

def _launch_volume(driver, identity, volume, size, userdata_content, network,
                    password=None, token=None, 
                    boot_index=0, shutdown=False, **kwargs):
    if not isinstance(driver.provider, OSProvider):
        raise ValueError("The Provider: %s can't create bootable volumes"
                         % driver.provider)
    extra_args = _extra_openstack_args(identity)
    kwargs.update(extra_args)
    boot_success, new_instance = driver.boot_volume(
            name=name, image=None, snapshot=None, volume=volume,
            boot_index=boot_index, shutdown=shutdown,
            #destination_type=destination_type,
            volume_size=None, size=size, networks=[network],
            ex_admin_pass=password, **kwargs)
    return (new_instance, token, password)
    
def _launch_machine(driver, identity, machine, size,
        name, userdata_content=None, network=None,
        password=None, token=None, **kwargs):
    if isinstance(driver.provider, EucaProvider):
        #Create/deploy the instance -- NOTE: Name is passed in extras
        logger.info("EUCA -- driver.create_instance EXTRAS:%s" % kwargs)
        esh_instance = driver\
            .create_instance(name=name, image=machine, size=size,
                    ex_userdata=userdata_contents, **kwargs)
    elif isinstance(driver.provider, OSProvider):
        deploy = True
        #ex_metadata, ex_keyname
        extra_args = _extra_openstack_args(identity)
        kwargs.update(extra_args)
        logger.debug("OS driver.create_instance kwargs: %s" % kwargs)
        esh_instance = driver.create_instance(
                name=name, image=machine, size=size,
                token=token, 
                networks=[network], ex_admin_pass=password,
                deploy=True, **kwargs)
        #Used for testing.. Eager ignores countdown
        if app.conf.CELERY_ALWAYS_EAGER:
            logger.debug("Eager Task, wait 1 minute")
            time.sleep(1*60)
    elif isinstance(driver.provider, AWSProvider):
        #TODO:Extra stuff needed for AWS provider here
        esh_instance = driver.deploy_instance(
                name=name, image=machine,
                size=size, deploy=True,
                token=token, **kwargs)
    else:
        raise Exception("Unable to launch with this provider.")
    return (esh_instance, token, password)

def _pre_launch_instance(driver, identity, size, name, **kwargs):
    """
    Returns:
    * Prep kwargs (username, password, token, & name)
    * User data (If Applicable)
    * LC Network (If Applicable)
    """
    prep_kwargs = _pre_launch_instance_kwargs(driver, identity, name)
    userdata = network = None
    if isinstance(driver.provider, EucaProvider)\
    or isinstance(driver.provider, AWSProvider):
        userdata = _generate_userdata_content(name, **prep_kwargs)
    elif isinstance(driver.provider, OSProvider):
        network = _provision_openstack_instance(identity)
    return prep_kwargs, userdata, network

def _pre_launch_instance_kwargs(driver, identity, instance_name,
        token=None, password=None, username=None, **kwargs):
    """
    For now, return prepared arguments as kwargs
    
    NOTE: For some providers (Like OpenStack) provisioning 
    """
    if not token:
        token = _get_token()
    if not username:
        username = _get_username(driver, identity)
    if not password:
        password = _get_password(username)
    return {
            "token": token,
            "username": username,
            "password": password,
           }

def _select_copy_source(copy_source):
    image = snapshot = volume = None
    if type(copy_source) == Machine:
        image = copy_source
    #if type(copy_source) == SnapShot:
    #    snapshot = copy_source
    if type(copy_source) == Volume:
        volume = copy_source
    return (image, snapshot, volume)

def _generate_userdata_content(name, username, token=None, password=None, init_file="v1"):
    instance_service_url = "%s" % (settings.INSTANCE_SERVICE_URL,)
    #Get a cleaned name
    name = slugify(unicode(name))
    userdata_contents = _get_init_script(instance_service_url,
                                         token,
                                         password,
                                         name,
                                         username, init_file)
    return userdata_content

def _complete_launch_instance(driver, identity, instance, user, token, password):
    from service import task
    # call async task to deploy to instance.
    task.deploy_init_task(driver, instance, identity, user.username, password, token)
    #Create the Core/DB for instance
    core_instance = convert_esh_instance(
        driver, instance, identity.provider.uuid, identity.uuid,
        user, token, password)
    #Update InstanceStatusHistory
    _first_update(driver, identity, core_instance, instance)
    #Invalidate and return
    invalidate_cached_instances(identity=identity)
    return core_instance

def _first_update(driver, identity, core_instance, esh_instance):
    #Prepare/Create the history based on 'core_instance' size
    esh_size = _get_size(driver, esh_instance)
    core_size = convert_esh_size(esh_size, identity.provider.uuid)
    history = core_instance.update_history(
        core_instance.esh.extra['status'],
        core_size,
        #3rd arg is task OR tmp_status
        core_instance.esh.extra.get('task') or
        core_instance.esh.extra.get('metadata', {}).get('tmp_status'),
        first_update=True)
    return history


def _get_username(driver, core_identity):
    try:
        username = driver.identity.user.username
    except Exception, no_username:
        username = core_identity.created_by.username
def _get_token():
    return generate_uuid4()
def _get_password(username):
    return generate_uuid4()
def generate_uuid4():
    return str(uuid.uuid4())
################################


def check_size(esh_driver, size_alias, provider_uuid):
    try:
        esh_size = esh_driver.get_size(size_alias)
        if not convert_esh_size(esh_size, provider_uuid).active():
            raise SizeNotAvailable()
        return esh_size
    except:
        raise SizeNotAvailable()


def get_boot_source(username, identity_uuid, source_identifier):
    try:
        identity = CoreIdentity.objects.get(
                uuid=identity_uuid)
        driver = get_cached_driver(identity=identity)
        sources = InstanceSource.current_sources()
        boot_source = sources.get(
                provider=identity.provider,
                identifier=source_identifier)
        return boot_source
    except CoreIdentity.DoesNotExist:
        raise Exception("Identity %s does not exist" % identity_uuid)
    except InstanceSource.DoesNotExist:
        raise Exception("No boot source found with identifier %s"
                % source_identifier)



def check_application_threshold(username, identity_uuid, esh_size, machine_alias):
    """
    """
    application = Application.objects.filter(
            providermachine__identifier=machine_alias).distinct().get()
    threshold = application.get_threshold()
    if not threshold:
        return
    #NOTE: Should be MB to MB test
    if esh_size.ram < threshold.memory_min:
        raise UnderThresholdError("This application requires >=%s GB of RAM."
                " Please re-launch with a larger size."
                % int(threshold.memory_min/1024))
    if esh_size.disk < threshold.storage_min:
        raise UnderThresholdError("This application requires >=%s GB of Disk."
                " Please re-launch with a larger size."
                % threshold.storage_min)





def check_quota(username, identity_uuid, esh_size, resuming=False):
    (over_quota, resource,
     requested, used, allowed) = check_over_quota(username,
                                                  identity_uuid,
                                                  esh_size, resuming=resuming)
    if over_quota and settings.ENFORCING:
        raise OverQuotaError(resource, requested, used, allowed)
    (over_allocation, time_diff) =\
        check_over_allocation(username,
                              identity_uuid)
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




#def launch_esh_instance(driver, source_alias, size_alias, core_identity,
#        name=None, username=None, using_admin=False, *args, **kwargs):
#
#    """
#    return 3-tuple: (esh_instance, instance_token, instance_password)
#    """
#    from service import task
#    try:
#        #create a reference to this attempted instance launch.
#        instance_token = str(uuid.uuid4())
#        #create a unique one-time password for instance root user
#        instance_password = str(uuid.uuid4())
#
#        #TODO: Mock these for faster launch performance
#
#        #Gather the machine object
#        boot_source = driver.get_machine(source_alias)
#        if not boot_source:
#            raise Exception(
#                "Machine %s could not be located with this driver"
#                % source_alias)
#
#        #Gather the size object
#        size = driver.get_size(size_alias)
#        if not size:
#            raise Exception(
#                "Size %s could not be located with this driver" % size_alias)
#
#        if not username:
#            username = driver.identity.user.username
#        if not name:
#            name = 'Instance of %s' % boot_source.alias
#
#    except Exception as e:
#        logger.exception(e)
#        raise


def _provision_openstack_instance(core_identity, admin_user=False):
    """
    TODO: "CloudAdministrators" logic goes here to dictate
          What we should do to provision an instance..
    """
    #NOTE: Admin users do NOT need a security group created for them!
    if not admin_user:
        security_group_init(core_identity)
    network = network_init(core_identity)
    keypair_init(core_identity)
    return network

def _extra_openstack_args(core_identity):
    credentials = core_identity.get_credentials()
    username = core_identity.created_by.username
    #username = credentials.get('key')
    tenant_name = credentials.get('ex_tenant_name')
    ex_metadata = {'tmp_status': 'initializing',
                   'tenant_name': tenant_name,
                   'creator': '%s' % username}
    ex_keyname = settings.ATMOSPHERE_KEYPAIR_NAME
    return {"ex_metadata":ex_metadata, "ex_keyname":ex_keyname}

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
    subnet = network_resources['subnets']
    if not network or not subnet:
        network, subnet = accounts.create_network(core_identity)
    else:
        network = network[0]
        subnet = subnet[0]
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

def _repair_instance_networking(esh_driver, esh_instance, provider_uuid, identity_uuid):
    from service.tasks.driver import \
            add_floating_ip, wait_for_instance, \
            deploy_init_to, deploy_failed, update_metadata
    logger.info("Instance %s needs to create and attach port instead"
                % esh_instance.id)
    core_identity = CoreIdentity.objects.get(uuid=identity_uuid)
    provider = Provider.objects.get(uuid=provider_uuid)
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
    final_update.pop('tmp_status',None)
    final_update.pop('iplant_suspend_fix',None)
    remove_status_task = update_metadata.si(
            esh_driver.__class__, esh_driver.provider, esh_driver.identity,
            esh_instance.id, final_update, replace_metadata=True)
    deploy_task.link(remove_status_task)

    #Attempt to redeploy after the restart..
    init_task.link(deploy_task)
    init_task.apply_async()
    return


def _check_volume_attachment(driver, instance):
    try:
        volumes = driver.list_volumes()
    except Exception as exc:
        # Ignore 'safe' errors related to
        # no floating IP
        # or no Volume capabilities.
        if ("500 Internal Server Error" in exc.message):
            return True
        raise
    for vol in volumes:
        attachment_set = vol.extra.get('attachments',[])
        if not attachment_set:
            continue
        for attachment in attachment_set:
            if instance.alias == attachment['serverId']:
                raise VolumeAttachConflict(instance.alias, vol.alias)
    return False
