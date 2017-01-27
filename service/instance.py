import os.path
import time
import uuid

from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django.utils.timezone import datetime
from djcelery.app import app

from threepio import logger, status_logger

from rtwo.models.provider import AWSProvider, AWSUSEastProvider,\
    AWSUSWestProvider, EucaProvider,\
    OSProvider, OSValhallaProvider
from rtwo.driver import OSDriver
from rtwo.drivers.common import _connect_to_keystone_v3, _token_to_keystone_scoped_project
from rtwo.drivers.openstack_network import NetworkManager
from rtwo.models.machine import Machine
from rtwo.models.size import MockSize
from rtwo.models.volume import Volume
from rtwo.exceptions import LibcloudHTTPError  # Move into rtwo.exceptions later...
from libcloud.common.exceptions import BaseHTTPError  # Move into rtwo.exceptions later...

from core.query import only_current
from core.models.instance_source import InstanceSource
from core.models.ssh_key import get_user_ssh_keys
from core.models.application import Application
from core.models.identity import Identity as CoreIdentity
from core.models.instance import convert_esh_instance, find_instance
from core.models.instance_action import InstanceAction
from core.models.size import convert_esh_size
from core.models.machine import ProviderMachine
from core.models.volume import convert_esh_volume
from core.models.provider import AccountProvider, Provider, ProviderInstanceAction

from atmosphere import settings
from atmosphere.settings import secrets

from service.cache import get_cached_driver, invalidate_cached_instances
from service.driver import _retrieve_source, get_account_driver
from service.licensing import _test_license
from service.networking import get_topology_cls, ExternalRouter, ExternalNetwork, _get_unique_id
from service.exceptions import (
    OverAllocationError, OverQuotaError, SizeNotAvailable,
    HypervisorCapacityError, SecurityGroupNotCreated,
    VolumeAttachConflict, VolumeDetachConflict, UnderThresholdError, ActionNotAllowed,
    socket_error, ConnectionFailure, InstanceDoesNotExist, LibcloudInvalidCredsError,
    Unauthorized)

from service.accounts.openstack_manager import AccountDriver as OSAccountDriver


def _get_size(esh_driver, esh_instance):
    if isinstance(esh_instance.size, MockSize):
        size = esh_driver.get_size(esh_instance.size.id)
    else:
        size = esh_instance.size
    return size


def _permission_to_act(identity_uuid, action_name, raise_exception=True):
    try:
        core_identity = CoreIdentity.objects.get(uuid=identity_uuid)
    except CoreIdentity.DoesNotExist:
        if raise_exception:
            raise
        logger.warn("Identity %s Does Not Exist!" % identity_uuid)
        return False

    try:
        test = ProviderInstanceAction.objects.get(
            instance_action__name=action_name,
            provider=core_identity.provider)
        if not test.enabled and raise_exception:
            raise ActionNotAllowed("This Action is disabled:%s"
                                   % (action_name,))
        return test.enabled
    except ProviderInstanceAction.DoesNotExist:
        logger.warn(
            "Permission to execute Instance Action: %s not found for Provider: %s. Default Behavior is to allow!" %
            (action_name, core_identity.provider))
        return True


def reboot_instance(
        esh_driver,
        esh_instance,
        identity_uuid,
        user,
        reboot_type="SOFT"):
    """
    Default to a soft reboot, but allow option for hard reboot.
    """
    # NOTE: We need to check the quota as if the instance were rebooting,
    #      Because in some cases, a reboot is required to get out of the
    #      suspended state..
    if reboot_type == "SOFT":
        _permission_to_act(identity_uuid, "Reboot")
    else:
        _permission_to_act(identity_uuid, "Hard Reboot")
    size = _get_size(esh_driver, esh_instance)
    esh_driver.reboot_instance(esh_instance, reboot_type=reboot_type)
    # reboots take very little time..
    core_identity = CoreIdentity.objects.get(uuid=identity_uuid)
    redeploy_init(esh_driver, esh_instance, core_identity)


def resize_instance(esh_driver, esh_instance, size_alias,
                    provider_uuid, identity_uuid, user):
    _permission_to_act(identity_uuid, "Resize")
    size = esh_driver.get_size(size_alias)
    redeploy_task = resize_and_redeploy(
        esh_driver,
        esh_instance,
        identity_uuid)
    esh_driver.resize_instance(esh_instance, size)
    redeploy_task.apply_async()
    # Write build state for new size
    update_status(
        esh_driver,
        esh_instance.id,
        provider_uuid,
        identity_uuid,
        user)


def confirm_resize(
        esh_driver,
        esh_instance,
        provider_uuid,
        identity_uuid,
        user):
    _permission_to_act(identity_uuid, "Resize")
    esh_driver.confirm_resize_instance(esh_instance)
    # Double-Check we are counting on new size
    update_status(
        esh_driver,
        esh_instance.id,
        provider_uuid,
        identity_uuid,
        user)


def stop_instance(esh_driver, esh_instance, provider_uuid, identity_uuid, user,
                  reclaim_ip=True):
    """

    raise OverQuotaError, OverAllocationError, LibcloudInvalidCredsError
    """
    _permission_to_act(identity_uuid, "Stop")
    if reclaim_ip:
        remove_ips(esh_driver, esh_instance, identity_uuid)
    stopped = esh_driver.stop_instance(esh_instance)
    if reclaim_ip:
        remove_empty_network(esh_driver, identity_uuid, {"skip_network":True})
    update_status(
        esh_driver,
        esh_instance.id,
        provider_uuid,
        identity_uuid,
        user)
    invalidate_cached_instances(
        identity=CoreIdentity.objects.get(uuid=identity_uuid))


def start_instance(esh_driver, esh_instance,
                   provider_uuid, identity_uuid, user,
                   restore_ip=True, update_meta=True):
    """

    raise OverQuotaError, OverAllocationError, LibcloudInvalidCredsError
    """
    # Don't check capacity because.. I think.. its already being counted.
    _permission_to_act(identity_uuid, "Start")
    if restore_ip:
        restore_network(esh_driver, esh_instance, identity_uuid)
        deploy_task = restore_ip_chain(
            esh_driver, esh_instance, redeploy=True,
            # NOTE: after removing FIXME, This
            # parameter can be removed as well
            core_identity_uuid=identity_uuid)

    needs_fixing = esh_instance.extra['metadata'].get('iplant_suspend_fix')
    logger.info("Instance %s needs to hard reboot instead of start" %
                esh_instance.id)
    if needs_fixing:
        return _repair_instance_networking(
            esh_driver,
            esh_instance,
            provider_uuid,
            identity_uuid)

    esh_driver.start_instance(esh_instance)
    if restore_ip:
        deploy_task.apply_async(countdown=10)
    update_status(
        esh_driver,
        esh_instance.id,
        provider_uuid,
        identity_uuid,
        user)
    invalidate_cached_instances(
        identity=CoreIdentity.objects.get(
            uuid=identity_uuid))


def suspend_instance(esh_driver, esh_instance,
                     provider_uuid, identity_uuid,
                     user, reclaim_ip=True):
    """

    raise OverQuotaError, OverAllocationError, LibcloudInvalidCredsError
    """
    _permission_to_act(identity_uuid, "Suspend")
    if reclaim_ip:
        remove_ips(esh_driver, esh_instance, identity_uuid)
    suspended = esh_driver.suspend_instance(esh_instance)
    if reclaim_ip:
        remove_empty_network(esh_driver, identity_uuid, {"skip_network":True})
    update_status(
        esh_driver,
        esh_instance.id,
        provider_uuid,
        identity_uuid,
        user)
    invalidate_cached_instances(
        identity=CoreIdentity.objects.get(
            uuid=identity_uuid))
    return suspended


# Networking specific
def remove_ips(esh_driver, esh_instance, identity_uuid, update_meta=True):
    """
    Returns: (floating_removed, fixed_removed)
    """
    from service.tasks.driver import update_metadata
    core_identity = Identity.objects.get(uuid=core_identity_uuid)
    network_driver = _to_network_driver(core_identity)
    result = network_driver.disassociate_floating_ip(esh_instance.id)
    logger.info("Removed Floating IP for Instance %s - Result:%s"
                % (esh_instance.id, result))
    if update_meta:
        driver_class = esh_driver.__class__
        identity = esh_driver.identity
        provider = esh_driver.provider

        metadata={'public-ip': '', 'public-hostname': ''}
        update_metadata.s(driver_class, provider, identity, esh_instance.id,
                          metadata, replace_metadata=False).apply()
    # Fixed
    instance_ports = network_driver.list_ports(device_id=esh_instance.id)
    if instance_ports:
        fixed_ip_port = instance_ports[0]
        fixed_ips = fixed_ip_port.get('fixed_ips', [])
        if fixed_ips:
            fixed_ip = fixed_ips[0]['ip_address']
            result = esh_driver._connection.ex_remove_fixed_ip(
                esh_instance,
                fixed_ip)
            logger.info("Removed Fixed IP %s - Result:%s" % (fixed_ip, result))
        return (True, True)
    return (True, False)

# Not in use -- marked for deletion
# def detach_port(esh_driver, esh_instance):
#     instance_ports = network_manager.list_ports(device_id=esh_instance.id)
#     if instance_ports:
#         fixed_ip_port = instance_ports[0]
#         result = esh_driver._connection.ex_detach_interface(
#             esh_instance.id, fixed_ip_port['id'])
#         logger.info("Detached Port: %s - Result:%s" % (fixed_ip_port, result))
#     return result


def remove_empty_network(esh_driver, identity_uuid, network_options={}):
    """
    #FIXME: I think the original intent of why we called this was:
    # 1. IF you are the last instance, remove the network.
    # 2. Remove the fixed IP that was allocated for the instance.
    # If so, i don't believe #2 is being completed
    """
    from service.tasks.driver import remove_empty_network as remove_empty_network_task
    remove_empty_network_task.s(
        esh_driver.__class__, esh_driver.provider,
        esh_driver.identity, identity_uuid, network_options).apply_async()


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

    # Get network name from fixed IP metadata 'addresses'
    node_network = esh_instance.extra.get('addresses')
    if node_network:
        network_id = _extract_network_metadata(
            network_manager,
            esh_instance,
            node_network)
    if not network_id:
        tenant_nets = network_manager.tenant_networks()
        if tenant_nets:
            network_id = tenant_nets[0]["id"]
    if not network_id:
        raise Exception("NetworkManager Could not determine the network"
                        "for node %s" % esh_instance)
    return network_id

# Celery Chain-Starters and Tasks


def resize_and_redeploy(esh_driver, esh_instance, core_identity_uuid):
    """
    TODO: Remove this and use the 'deploy_init' tasks already written instead!
          -Steve 2/2015
    Use this function to kick off the async task when you ONLY want to deploy
    (No add fixed, No add floating)
    """
    from service.tasks.driver import deploy_init_to
    from service.tasks.driver import wait_for_instance, complete_resize
    from service.deploy import deploy_test
    touch_script = deploy_test()
    core_identity = CoreIdentity.objects.get(uuid=core_identity_uuid)

    task_one = wait_for_instance.s(
        esh_instance.id, esh_driver.__class__, esh_driver.provider,
        esh_driver.identity, "verify_resize")
    raise Exception("Programmer -- Fix this method based on the TODO")
    # task_two = deploy_script.si(
    #     esh_driver.__class__, esh_driver.provider,
    #     esh_driver.identity, esh_instance.id, touch_script)
    task_three = complete_resize.si(
        esh_driver.__class__, esh_driver.provider,
        esh_driver.identity, esh_instance.id,
        core_identity.provider.id, core_identity.id, core_identity.created_by)
    task_four = deploy_init_to.si(
        esh_driver.__class__, esh_driver.provider,
        esh_driver.identity, esh_instance.id, core_identity, redeploy=True)
    # Link em all together!
    task_one.link(task_two)
    task_two.link(task_three)
    task_three.link(task_four)
    return task_one


def redeploy_instance(
        esh_driver,
        esh_instance,
        username,
        force_redeploy=False):
    """
    EXPERIMENTAL.

    Starts redeployment of an instance using the tmp_status metadata.

    NOTE: Not used by API. See redeploy_init.
    """
    from service.tasks.driver import get_idempotent_deploy_chain
    if force_redeploy or esh_instance.extra.get('metadata').get(
            'tmp_status',
            None) == "":
        esh_instance.extra['metadata']['tmp_status'] = "initializing"
    deploy_chain = get_idempotent_deploy_chain(
        esh_driver.__class__, esh_driver.provider, esh_driver.identity,
        esh_instance, username)
    return deploy_chain.apply_async()


def redeploy_init(esh_driver, esh_instance, core_identity):
    """
    Use this function to kick off the async task when you ONLY want to deploy
    (No add fixed, No add floating)
    """
    from service.tasks.driver import deploy_init_to
    logger.info("Add floating IP and Deploy")
    deploy_init_to.s(esh_driver.__class__, esh_driver.provider,
                     esh_driver.identity, esh_instance.id,
                     core_identity, redeploy=True).apply_async()


def restore_ip_chain(esh_driver, esh_instance, redeploy=False,
                     core_identity_uuid=None):
    """
    Returns: a task, chained together
    task chain: wait_for("active") --> set tmp_status to 'initializing' --> AddFixed --> AddFloating
    --> reDeploy
    start with: task.apply_async()
    """
    from service.tasks.driver import (
        wait_for_instance, add_fixed_ip, add_floating_ip,
        deploy_init_to, update_metadata
    )
    init_task = wait_for_instance.s(
        esh_instance.id, esh_driver.__class__, esh_driver.provider,
        esh_driver.identity, "active",
        # TODO: DELETEME below.
        no_tasks=True)
    # Step 1: Set metadata to initializing
    metadata = {'tmp_status': 'initializing'}
    metadata_update_task = update_metadata.si(
        esh_driver.__class__, esh_driver.provider, esh_driver.identity,
        esh_instance.id, metadata, replace_metadata=False)

    # Step 2: Add fixed
    fixed_ip_task = add_fixed_ip.si(
        esh_driver.__class__, esh_driver.provider,
        esh_driver.identity, esh_instance.id, core_identity_uuid)

    init_task.link(metadata_update_task)
    metadata_update_task.link(fixed_ip_task)
    # Add float and re-deploy OR just add floating IP...
    if redeploy:
        core_identity = CoreIdentity.objects.get(uuid=core_identity_uuid)
        deploy_task = deploy_init_to.si(
            esh_driver.__class__,
            esh_driver.provider,
            esh_driver.identity,
            esh_instance.id,
            core_identity,
            redeploy=True)
        fixed_ip_task.link(deploy_task)
    else:
        logger.info("Skip deployment, Add floating IP only")
        floating_ip_task = add_floating_ip.si(
            esh_driver.__class__,
            esh_driver.provider,
            esh_driver.identity,
            str(core_identity.uuid),
            esh_instance.id)
        fixed_ip_task.link(floating_ip_task)
    return init_task


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
    # CPU tests first (Most likely bottleneck)
    cpu_total = hypervisor_stats['vcpus']
    cpu_used = hypervisor_stats['vcpus_used']
    cpu_needed = instance.size.cpu
    log_str = "Resource:%s Used:%s Additional:%s Total:%s"\
        % ("cpu", cpu_used, cpu_needed, cpu_total)
    logger.debug(log_str)
    if cpu_used + cpu_needed > cpu_total:
        raise HypervisorCapacityError(
            hypervisor_hostname,
            "Hypervisor is over-capacity. %s" %
            log_str)

    # ALL MEMORY VALUES IN MB
    mem_total = hypervisor_stats['memory_mb']
    mem_used = hypervisor_stats['memory_mb_used']
    mem_needed = instance.size.ram
    log_str = "Resource:%s Used:%s Additional:%s Total:%s"\
        % ("mem", mem_used, mem_needed, mem_total)
    logger.debug(log_str)
    if mem_used + mem_needed > mem_total:
        raise HypervisorCapacityError(
            hypervisor_hostname,
            "Hypervisor is over-capacity. %s" %
            log_str)

    # ALL DISK VALUES IN GB
    disk_total = hypervisor_stats['local_gb']
    disk_used = hypervisor_stats['local_gb_used']
    disk_needed = instance.size.disk + instance.size.ephemeral
    log_str = "Resource:%s Used:%s Additional:%s Total:%s"\
        % ("disk", disk_used, disk_needed, disk_total)
    if disk_used + disk_needed > disk_total:
        raise HypervisorCapacityError(
            hypervisor_hostname,
            "Hypervisor is over-capacity. %s" %
            log_str)


def resume_instance(esh_driver, esh_instance,
                    provider_uuid, identity_uuid,
                    user, restore_ip=True,
                    update_meta=True):
    """
    raise OverQuotaError, OverAllocationError, LibcloudInvalidCredsError
    """
    from service.tasks.driver import _update_status_log
    _permission_to_act(identity_uuid, "Resume")
    _update_status_log(esh_instance, "Resuming Instance")
    size = _get_size(esh_driver, esh_instance)
    if restore_ip:
        restore_network(esh_driver, esh_instance, identity_uuid)
        deploy_task = restore_ip_chain(esh_driver, esh_instance, redeploy=True,
                                       # NOTE: after removing FIXME, This
                                       # parameter can be removed as well
                                       core_identity_uuid=identity_uuid)
    # FIXME: These three lines are necessary to repair our last network outage.
    # At some point, we should re-evaluate when it is safe to remove
    needs_fixing = esh_instance.extra['metadata'].get('iplant_suspend_fix')
    if needs_fixing:
        return _repair_instance_networking(
            esh_driver,
            esh_instance,
            provider_uuid,
            identity_uuid)

    esh_driver.resume_instance(esh_instance)
    if restore_ip:
        deploy_task.apply_async()


def shelve_instance(esh_driver, esh_instance,
                    provider_uuid, identity_uuid,
                    user, reclaim_ip=True):
    """

    raise OverQuotaError, OverAllocationError, LibcloudInvalidCredsError
    """
    from service.tasks.driver import _update_status_log
    _permission_to_act(identity_uuid, "Shelve")
    _update_status_log(esh_instance, "Shelving Instance")
    if reclaim_ip:
        remove_ips(esh_driver, esh_instance, identity_uuid)
    shelved = esh_driver._connection.ex_shelve_instance(esh_instance)
    if reclaim_ip:
        remove_empty_network(esh_driver, identity_uuid, {"skip_network":True})
    update_status(
        esh_driver,
        esh_instance.id,
        provider_uuid,
        identity_uuid,
        user)
    invalidate_cached_instances(
        identity=CoreIdentity.objects.get(
            uuid=identity_uuid))
    return shelved


def unshelve_instance(esh_driver, esh_instance,
                      provider_uuid, identity_uuid,
                      user, restore_ip=True,
                      update_meta=True):
    """
    raise OverQuotaError, OverAllocationError, LibcloudInvalidCredsError
    """
    from service.tasks.driver import _update_status_log
    _permission_to_act(identity_uuid, "Unshelve")
    _update_status_log(esh_instance, "Unshelving Instance")
    size = _get_size(esh_driver, esh_instance)
    admin_capacity_check(provider_uuid, esh_instance.id)
    if restore_ip:
        restore_network(esh_driver, esh_instance, identity_uuid)
        deploy_task = restore_ip_chain(esh_driver, esh_instance, redeploy=True,
                                       # NOTE: after removing FIXME, This
                                       # parameter can be removed as well
                                       core_identity_uuid=identity_uuid)

    unshelved = esh_driver._connection.ex_unshelve_instance(esh_instance)
    if restore_ip:
        deploy_task.apply_async(countdown=10)
    return unshelved


def offload_instance(esh_driver, esh_instance,
                     provider_uuid, identity_uuid,
                     user, reclaim_ip=True):
    """

    raise OverQuotaError, OverAllocationError, LibcloudInvalidCredsError
    """
    from service.tasks.driver import _update_status_log
    _permission_to_act(identity_uuid, "Shelve Offload")
    _update_status_log(esh_instance, "Shelve-Offloading Instance")
    if reclaim_ip:
        remove_ips(esh_driver, esh_instance, identity_uuid)
    offloaded = esh_driver._connection.ex_shelve_offload_instance(esh_instance)
    if reclaim_ip:
        remove_empty_network(esh_driver, identity_uuid, {"skip_network":True})
    update_status(
        esh_driver,
        esh_instance.id,
        provider_uuid,
        identity_uuid,
        user)
    invalidate_cached_instances(
        identity=CoreIdentity.objects.get(
            uuid=identity_uuid))
    return offloaded


def destroy_instance(user, core_identity_uuid, instance_alias):
    """
    Use this function to destroy an instance (From the API, or the REPL)
    """
    # TODO: Test how this f(n) works when called multiple times
    success, esh_instance = _destroy_instance(
        core_identity_uuid, instance_alias)
    if not success and esh_instance:
        raise Exception("Instance could not be destroyed")
    elif esh_instance:
        os_cleanup_networking(core_identity_uuid)
        core_instance = end_date_instance(
            user, esh_instance, core_identity_uuid)
        return core_instance
    else:
        # Edge case - If you attempt to delete more than once...
        core_instance = find_instance(instance_alias)
        return core_instance


def end_date_instance(user, esh_instance, core_identity_uuid):
    # Retrieve the 'hopefully now deleted' instance and end date it.
    identity = CoreIdentity.objects.get(uuid=core_identity_uuid)
    esh_driver = get_cached_driver(identity=identity)
    try:
        core_instance = convert_esh_instance(esh_driver, esh_instance,
                                             identity.provider.uuid,
                                             identity.uuid,
                                             user)
        #NOTE: We may want to ensure instances are *actually* terminated prior to end dating them.
        if core_instance:
            core_instance.end_date_all()
        return core_instance
    except (socket_error, ConnectionFailure):
        logger.exception("connection failure during destroy instance")
        return None
    except LibcloudInvalidCredsError:
        logger.exception("LibcloudInvalidCredsError during destroy instance")
        return None


def os_cleanup_networking(core_identity_uuid):
    """
    NOTE: this relies on celery to 'kick these tasks off' as we return the destroyed instance back to the user.
    """
    from service.tasks.driver import clean_empty_ips, remove_empty_network
    core_identity = CoreIdentity.objects.get(uuid=core_identity_uuid)
    driver = get_cached_driver(identity=core_identity)
    if not isinstance(driver, OSDriver):
        return
    # Spawn off the last two tasks
    logger.debug("OSDriver Logic -- Remove floating ips and check"
                 " for empty project")
    driverCls = driver.__class__
    provider = driver.provider
    identity = driver.identity
    instances = driver.list_instances()
    active_instances = [driver._is_active_instance(inst) for inst in instances]
    if not active_instances:
        logger.debug("Driver shows 0 of %s instances are active"
                     % (len(instances),))
        # For testing ONLY.. Test cases ignore countdown..
        if app.conf.CELERY_ALWAYS_EAGER:
            logger.debug("Eager task waiting 1 minute")
            time.sleep(60)
        clean_task = clean_empty_ips.si(driverCls, provider, identity,
                                        immutable=True, countdown=5)
        remove_task = remove_empty_network.si(
            driverCls, provider, identity, core_identity_uuid, {"skip_network":False},
            immutable=True, countdown=60)
        clean_task.link(remove_task)
        clean_task.apply_async()
    else:
        logger.debug("Driver shows %s of %s instances are active"
                     % (len(active_instances), len(instances)))
        # For testing ONLY.. Test cases ignore countdown..
        if app.conf.CELERY_ALWAYS_EAGER:
            logger.debug("Eager task waiting 15 seconds")
            time.sleep(15)
        destroy_chain = clean_empty_ips.si(
            driverCls, provider, identity,
            immutable=True, countdown=5)
        destroy_chain.apply_async()
    return

def _destroy_instance(identity_uuid, instance_alias):
    """
    Responsible for actually destroying the instance
    Return:
    Deleted, Instance
    """
    identity = CoreIdentity.objects.get(uuid=identity_uuid)
    esh_driver = get_cached_driver(identity=identity)
    # Bail if driver cant be created
    if not esh_driver:
        return (False, None)
    instance = esh_driver.get_instance(instance_alias)
    # Bail if instance doesnt exist
    if not instance:
        return (True, None)
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
    return (node_destroyed, instance)


# Private methods and helpers
def admin_get_instance(admin_driver, instance_id):
    instance_list = admin_driver.list_all_instances()
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
    # Grab a new copy of the instance

    if AccountProvider.objects.filter(identity__uuid=identity_uuid):
        esh_instance = admin_get_instance(esh_driver, instance_id)
    else:
        esh_instance = esh_driver.get_instance(instance_id)
    if not esh_instance:
        return None
    # Convert & Update based on new status change
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


def _pre_launch_validation(
        username,
        esh_driver,
        identity_uuid,
        boot_source,
        size):
    """
    Used BEFORE launching a volume/instance .. Raise exceptions here to be dealt with by the caller.
    """
    identity = CoreIdentity.objects.get(uuid=identity_uuid)

    # May raise OverQuotaError or OverAllocationError
    check_quota(username, identity_uuid, size,
            include_networking=True)

    # May raise UnderThresholdError
    check_application_threshold(username, identity_uuid, size, boot_source)

    if boot_source.is_machine():
        machine = _retrieve_source(
            esh_driver,
            boot_source.identifier,
            "machine")
        # may raise an exception if licensing doesnt match identity
        _test_for_licensing(machine, identity)


def launch_instance(user, identity_uuid,
                    size_alias, source_alias, name, deploy=True,
                    **launch_kwargs):
    """
    USE THIS TO LAUNCH YOUR INSTANCE FROM THE REPL!
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
    status_logger.debug(
        "%s,%s,%s,%s,%s,%s" %
        (now_time,
         user,
         "No Instance",
         source_alias,
         size_alias,
         "Request Received"))
    identity = CoreIdentity.objects.get(uuid=identity_uuid)
    provider_uuid = identity.provider.uuid

    esh_driver = get_cached_driver(identity=identity)

    # May raise Unauthorized/ConnectionFailure/SizeNotAvailable
    size = check_size(esh_driver, size_alias, provider_uuid)
    # May raise Exception("Volume/Machine not available")
    boot_source = get_boot_source(user.username, identity_uuid, source_alias)

    # Raise any other exceptions before launching here
    _pre_launch_validation(
        user.username,
        esh_driver,
        identity_uuid,
        boot_source,
        size)

    core_instance = _select_and_launch_source(
        user,
        identity_uuid,
        esh_driver,
        boot_source,
        size,
        name=name,
        deploy=deploy,
        **launch_kwargs)
    return core_instance


# NOTE: Harmonizing these four methods below would be nice..


"""
Actual Launch Methods
"""


def _select_and_launch_source(
        user,
        identity_uuid,
        esh_driver,
        boot_source,
        size,
        name,
        deploy=True,
        **launch_kwargs):
    """
    Select launch route based on whether boot_source is-a machine/volume
    """
    identity = CoreIdentity.objects.get(uuid=identity_uuid)
    if boot_source.is_volume():
        # NOTE: THIS route works when launching an EXISTING volume ONLY
        #      to CREATE a new bootable volume (from an existing volume/image/snapshot)
        #      use service/volume.py 'boot_volume'
        volume = _retrieve_source(esh_driver, boot_source.identifier, "volume")
        core_instance = launch_volume_instance(
            esh_driver, identity, volume, size, name,
            deploy=deploy, **launch_kwargs)
    elif boot_source.is_machine():
        machine = _retrieve_source(
            esh_driver,
            boot_source.identifier,
            "machine")
        core_instance = launch_machine_instance(
            esh_driver, identity, machine, size, name,
            deploy=deploy, **launch_kwargs)
    else:
        raise Exception("Boot source is of an unknown type")
    return core_instance


def boot_volume_instance(
        driver, identity, copy_source, size, name,
        # Depending on copy source, these specific kwargs may/may not be used.
        boot_index=0, shutdown=False, volume_size=None,
        # Other kwargs passed for future needs
        deploy=True, **kwargs):
    """
    Create a new volume and launch it as an instance
    """
    kwargs, userdata, network = _pre_launch_instance(
        driver, identity, size, name, **kwargs)
    kwargs.update(prep_kwargs)
    instance, token, password = _boot_volume(
        driver, identity, copy_source, size,
        name, userdata, network, **prep_kwargs)
    return _complete_launch_instance(
        driver, identity, instance,
        identity.created_by, token, password, deploy=deploy)


def launch_volume_instance(driver, identity, volume, size, name,
                           deploy=True, **kwargs):
    """
    Re-Launch an existing volume as an instance
    """
    kwargs, userdata, network = _pre_launch_instance(
        driver, identity, size, name, **kwargs)
    kwargs.update(prep_kwargs)
    instance, token, password = _launch_volume(
        driver, identity, volume, size,
        name, userdata, network, **kwargs)
    return _complete_launch_instance(driver, identity, instance,
                                     identity.created_by, token, password,
                                     deploy=deploy)


def launch_machine_instance(driver, identity, machine, size, name,
                            deploy=True, **kwargs):
    """
    Launch an existing machine as an instance
    """
    prep_kwargs, userdata, network = _pre_launch_instance(
        driver, identity, size, name, **kwargs)
    kwargs.update(prep_kwargs)
    instance, token, password = _launch_machine(
        driver, identity, machine, size,
        name, userdata, network, **kwargs)
    return _complete_launch_instance(driver, identity, instance,
                                     identity.created_by, token, password,
                                     deploy=deploy)


def _boot_volume(driver, identity, copy_source, size, name, userdata, network,
                 password=None, token=None,
                 boot_index=0, shutdown=False, **kwargs):
    image, snapshot, volume = _select_copy_source(copy_source)
    if not isinstance(driver.provider, OSProvider):
        raise ValueError("The Provider: %s can't create bootable volumes"
                         % driver.provider)
    extra_args = _extra_openstack_args(
        identity, ex_metadata={"bootable_volume": True})
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
        volume_size=None, size=size, networks=[network],
        ex_admin_pass=password, **kwargs)
    return (new_instance, token, password)


def _launch_machine(driver, identity, machine, size,
                    name, userdata_content=None, network=None,
                    password=None, token=None, **kwargs):
    if isinstance(driver.provider, OSProvider):
        deploy = True
        #ex_metadata, ex_keyname
        extra_args = _extra_openstack_args(identity)
        kwargs.update(extra_args)
        conn_kwargs = {'max_attempts': 1}
        logger.debug("OS driver.create_instance kwargs: %s" % kwargs)
        esh_instance = driver.create_instance(
            name=name, image=machine, size=size,
            token=token,
            networks=[network], ex_admin_pass=password,
            ex_connection_kwargs=conn_kwargs,
            **kwargs)
        # Used for testing.. Eager ignores countdown
        if app.conf.CELERY_ALWAYS_EAGER:
            logger.debug("Eager Task, wait 1 minute")
            time.sleep(1 * 60)
    elif isinstance(driver.provider, EucaProvider):
        # Create/deploy the instance -- NOTE: Name is passed in extras
        logger.info("EUCA -- driver.create_instance EXTRAS:%s" % kwargs)
        esh_instance = driver\
            .create_instance(name=name, image=machine, size=size,
                             ex_userdata=userdata_contents, **kwargs)
    elif isinstance(driver.provider, AWSProvider):
        # TODO:Extra stuff needed for AWS provider here
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


def _pre_launch_instance_kwargs(
        driver,
        identity,
        instance_name,
        token=None,
        password=None,
        username=None,
        **kwargs):
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
    if isinstance(copy_source, Machine):
        image = copy_source
    if isinstance(copy_source, Volume):
        volume = copy_source
    return (image, snapshot, volume)


def _generate_userdata_content(
        name,
        username,
        token=None,
        password=None,
        init_file="v1"):
    instance_service_url = "%s" % (settings.INSTANCE_SERVICE_URL,)
    # Get a cleaned name
    name = slugify(unicode(name))
    userdata_contents = _get_init_script(instance_service_url,
                                         token,
                                         password,
                                         name,
                                         username, init_file)
    return userdata_content


def _complete_launch_instance(
        driver,
        identity,
        instance,
        user,
        token,
        password,
        deploy=True):
    from service import task
    # Create the Core/DB for instance
    core_instance = convert_esh_instance(
        driver, instance, identity.provider.uuid, identity.uuid,
        user, token, password)
    # Update InstanceStatusHistory
    _first_update(driver, identity, core_instance, instance)
    # call async task to deploy to instance.
    task.deploy_init_task(driver, instance, identity, user.username,
                          password, token, deploy=deploy)
    # Invalidate and return
    invalidate_cached_instances(identity=identity)
    return core_instance


def _first_update(driver, identity, core_instance, esh_instance):
    # Prepare/Create the history based on 'core_instance' size
    esh_size = _get_size(driver, esh_instance)
    core_size = convert_esh_size(esh_size, identity.provider.uuid)
    history = core_instance.update_history(
        core_instance.esh.extra['status'],
        core_size,
        core_instance.esh.extra.get('task'),
        core_instance.esh.extra.get('metadata', {}).get('tmp_status'),
        first_update=True)
    return history


def _get_username(driver, core_identity):
    try:
        username = driver.identity.user.username
    except Exception as no_username:
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
    except LibcloudHTTPError as http_err:
        if http_err.code == 401:
            raise Unauthorized(http_err.message)
        raise ConnectionFailure(http_err.message)
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


def check_application_threshold(
        username,
        identity_uuid,
        esh_size,
        boot_source):
    """
    """
    core_identity = CoreIdentity.objects.get(uuid=identity_uuid)
    application = Application.objects.filter(
        versions__machines__instance_source__identifier=boot_source.identifier,
        versions__machines__instance_source__provider=core_identity.provider).distinct().get()
    try:
        threshold = boot_source.current_source.application_version.get_threshold()
    except:
        return

    if not threshold:
        return
    
    # NOTE: Should be MB to MB test
    if esh_size.ram < threshold.memory_min:
        raise UnderThresholdError("This application requires >=%s GB of RAM."
                                  " Please re-launch with a larger size."
                                  % int(threshold.memory_min / 1024))
    if esh_size.cpu < threshold.cpu_min:
        raise UnderThresholdError("This application requires >=%s CPU."
                                  " Please re-launch with a larger size."
                                  % threshold.cpu_min)
    return


def _test_for_licensing(esh_machine, identity):
    """
    Used to determine whether or not an instance should launch
    Returns True OR raise Exception with reason for failure
    """
    try:
        core_machine = ProviderMachine.objects.get(
            instance_source__identifier=esh_machine.id,
            instance_source__provider=identity.provider)
    except ProviderMachine.DoesNotExist:
        raise Exception(
            "Execution in workflow error! Trying to launch a provider machine, but it has not been added to the DB (convert_esh_machine is broken?)")
    app_version = core_machine.application_version
    if not app_version.licenses.count():
        return True
    for license in app_version.licenses.all():
        passed_test = _test_license(license, identity)
        if passed_test:
            return True
    app = app_version.application
    raise Exception(
        "Identity %s did not meet the requirements of the associated license on Application %s + Version %s" %
        (app.name, app_version.name))


def check_quota(username, identity_uuid, esh_size,
        include_networking=False):
    from service.monitoring import check_over_allocation
    from service.quota import check_over_instance_quota
    try:
        check_over_instance_quota(
            username, identity_uuid, esh_size,
            include_networking=include_networking)
    except ValidationError as bad_quota:
        raise OverQuotaError(message=bad_quota.message)

    if settings.USE_ALLOCATION_SOURCE:
        logger.info("Settings dictate that USE_ALLOCATION_SOURCE = True. A new method will be required to determine over-allocation based on the selected allocation_source. Returning..")
        return
    (over_allocation, time_diff) =\
        check_over_allocation(username,
                              identity_uuid)
    if over_allocation and settings.ENFORCING:
        raise OverAllocationError(time_diff)


def delete_security_group(core_identity):
    has_secret = core_identity.get_credential('secret') is not None
    if has_secret:
        return admin_delete_security_group(core_identity)
    return user_delete_security_group(core_identity)

def admin_delete_security_group(core_identity):
    os_acct_driver = get_account_driver(core_identity.provider)
    os_acct_driver.delete_security_group(core_identity)

def user_delete_security_group(core_identity):
    network_driver = _to_network_driver(core_identity)
    driver = get_cached_driver(identity=core_identity)
    security_groups = driver._connection.ex_list_security_groups()
    for security_group in security_groups:
        try:
            driver._connection.ex_delete_security_group(security_group)
        except:
            # Try as neutron
            network_driver.neutron.delete_security_group(security_group.id)
    return


def security_group_init(core_identity, max_attempts=3):
    has_secret = core_identity.get_credential('secret') is not None
    if has_secret:
        return admin_security_group_init(core_identity)
    return user_security_group_init(core_identity)


def user_security_group_init(core_identity, security_group_name='default'):
    # Rules can come from the provider _or_ from settings _otherwise_ empty-list
    rules = core_identity.provider.get_config('network', 'default_security_rules',getattr(settings,'DEFAULT_RULES',[]))
    driver = get_cached_driver(identity=core_identity)
    lc_driver = driver._connection
    security_group = get_or_create_security_group(lc_driver, security_group_name)
    set_security_group_rules(lc_driver, security_group, rules)
    return security_group


def set_security_group_rules(lc_driver, security_group, rules):
    for rule_tuple in rules:
        if len(rule_tuple) == 3:
            (ip_protocol, from_port, to_port) = rule_tuple
            cidr = None
        elif len(rule_tuple) == 4:
            (ip_protocol, from_port, to_port, cidr) = rule_tuple
        else:
            raise Exception("Invalid DEFAULT_RULES contain a rule, %s, which does not match the expected format" % rule_tuple)

        try:
            # attempt to find 
            rule_found = any(
                sg_rule for sg_rule in security_group.rules
                if sg_rule.ip_protocol == ip_protocol.lower() and
                sg_rule.from_port == from_port and
                sg_rule.to_port == to_port and
                (not cidr or sg_rule.ip_range == cidr))
            if rule_found:
                continue
            # Attempt to create
            lc_driver.ex_create_security_group_rule(security_group, ip_protocol, from_port, to_port, cidr)
        except BaseHTTPError as exc:
            if "Security group rule already exists" in exc.message:
                continue
            raise
    return security_group

def get_or_create_security_group(lc_driver, security_group_name):
    sgroup_list = lc_driver.ex_list_security_groups()
    security_group = [sgroup for sgroup in sgroup_list if sgroup.name == security_group_name]
    if len(security_group) > 0:
        security_group = security_group[0]
    else:
        security_group = lc_driver.ex_create_security_group(security_group_name,'Security Group created by Atmosphere')

    if security_group is None:
       raise Exception("Could not find or create security group")
    return security_group

def admin_security_group_init(core_identity, max_attempts=3):
    os_driver = OSAccountDriver(core_identity.provider)
    # TODO: Remove kludge when openstack connections can be
    # Deemed reliable. Otherwise generalize this pattern so it
    # can be arbitrarilly applied to any call that is deemed 'unstable'.
    # -Steve
    attempt = 0
    while attempt < max_attempts:
        attempt += 1
        security_group = os_driver.init_security_group(core_identity)
        if security_group:
            return security_group
        time.sleep(2**attempt)
    raise SecurityGroupNotCreated()


def keypair_init(core_identity):
    return user_keypair_init(core_identity)


def user_keypair_init(core_identity):
    user = core_identity.created_by
    esh_driver = get_cached_driver(identity=core_identity)
    lc_driver = esh_driver._connection
    USERNAME = str(user.username)
    user_keys = get_user_ssh_keys(USERNAME)
    keys = []
    for user_key in user_keys:
        try:
            key = lc_driver.ex_import_keypair_from_string(user_key.name, user_key.pub_key)
            keys.append(key)
        except BaseHTTPError as exc:
            if "already exists" in exc.message:
                continue
            raise
    return user_keys


def admin_keypair_init(core_identity):
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
    return user_network_init(core_identity)


def _to_network_driver(core_identity):
    all_creds = core_identity.get_all_credentials()
    project_name = core_identity.project_name()
    domain_name = all_creds.get('domain_name', 'default')
    auth_url = all_creds.get('auth_url')
    if '/v' not in auth_url:  # Add /v3 if no version specified in auth_url
        auth_url += '/v3'
    if 'ex_force_auth_token' in all_creds:
        auth_token = all_creds['ex_force_auth_token']
        (auth, sess, token) = _token_to_keystone_scoped_project(
            auth_url, auth_token,
            project_name, domain_name)
    else:
        username = all_creds['key']
        password = all_creds['secret']
        (auth, sess, token) = _connect_to_keystone_v3(
            auth_url, username, password,
            project_name, domain_name)
    network_driver = NetworkManager(session=sess)
    return network_driver


def user_network_init(core_identity):
    """
    WIP -- need to figure out how to do this within the scope of libcloud // OR using existing authtoken to connect with neutron.
    """
    username = core_identity.get_credential('key')
    if not username:
        username = core_identity.created_by.username
    esh_driver = get_cached_driver(identity=core_identity)
    dns_nameservers = core_identity.provider.get_config('network', 'dns_nameservers', [])
    topology_name = core_identity.provider.get_config('network', 'topology', None)
    if not topology_name:
        logger.error(
            "Network topology not selected -- "
            "Will attempt to use the last known default: ExternalRouter.")
        topology_name = "External Router Topology"
    network_driver = _to_network_driver(core_identity)
    user_neutron = network_driver.neutron
    network_strategy = initialize_user_network_strategy(
        topology_name, core_identity, network_driver, user_neutron)
    network_resources = network_strategy.create(
        username=username, dns_nameservers=dns_nameservers)
    network_strategy.post_create_hook(network_resources)
    logger.info("Created user network - %s" % network_resources)
    network, subnet = network_resources['network'], network_resources['subnet']
    lc_network = _to_lc_network(esh_driver, network, subnet)
    return lc_network


def initialize_user_network_strategy(topology_name, identity, network_driver, neutron):
    """
    Select a network topology and initialize it with the identity/provider specific information required.
    """
    try:
        NetworkTopologyStrategyCls = get_topology_cls(topology_name)
        network_strategy = NetworkTopologyStrategyCls(identity, network_driver, neutron)
        # validate should raise exception if mis-configured.
        network_strategy.validate(identity)
    except:
        logger.exception(
            "Error initializing Network Topology - %s + %s " %
            (NetworkTopologyStrategyCls, identity))
        raise
    return network_strategy


def destroy_network(core_identity, options):
    has_secret = core_identity.get_credential('secret') is not None
    if has_secret:
        return admin_destroy_network(core_identity, options)
    return user_destroy_network(core_identity, options)


def admin_destroy_network(core_identity, options):
    topology_name = core_identity.provider.get_config('network', 'topology', None)
    if not topology_name:
        logger.error(
            "Network topology not selected -- "
            "Will attempt to use the last known default: ExternalRouter.")
        topology_name = "External Router Topology"
    os_acct_driver = get_account_driver(core_identity.provider)
    return os_acct_driver.delete_user_network(
        core_identity, options)

def user_destroy_network(core_identity, options):
    topology_name = core_identity.provider.get_config('network', 'topology', None)
    if not topology_name:
        logger.error(
            "Network topology not selected -- "
            "Will attempt to use the last known default: ExternalRouter.")
        topology_name = "External Router Topology"
    network_driver = _to_network_driver(core_identity)
    network_strategy = initialize_user_network_strategy(
        topology_name, core_identity, network_driver, network_driver.neutron)
    skip_network = options.get("skip_network", False)
    return network_strategy.delete(skip_network=skip_network)


def admin_network_init(core_identity):
    os_driver = OSAccountDriver(core_identity.provider)
    network_resources = os_driver.create_user_network(core_identity)
    logger.info("Created user network - %s" % network_resources)
    network, subnet = network_resources['network'], network_resources['subnet']
    lc_network = _to_lc_network(os_driver.admin_driver, network, subnet)
    return lc_network


def _to_lc_network(driver, network, subnet):
    from libcloud.compute.drivers.openstack import OpenStackNetwork
    lc_network = OpenStackNetwork(
        network['id'],
        network['name'],
        subnet['cidr'],
        driver,
        {"network": network,
         "subnet": subnet})
    return lc_network


def _provision_openstack_instance(core_identity, admin_user=False):
    """
    TODO: "CloudAdministrators" logic goes here to dictate
          What we should do to provision an instance..
    """
    # NOTE: Admin users do NOT need a security group created for them!
    if not admin_user:
        security_group_init(core_identity)
    network = network_init(core_identity)
    keypair_init(core_identity)
    return network


def _extra_openstack_args(core_identity, ex_metadata={}):
    credentials = core_identity.get_credentials()
    username = core_identity.created_by.username
    tenant_name = credentials.get('ex_tenant_name')
    has_secret = credentials.get('secret') is not None
    ex_metadata.update({'tmp_status': 'initializing',
                        'tenant_name': tenant_name,
                        'creator': '%s' % username})
    if has_secret and getattr(settings, 'ATMOSPHERE_KEYPAIR_NAME'):
        ex_keyname = settings.ATMOSPHERE_KEYPAIR_NAME
    else:
        user = core_identity.created_by
        user_keys = get_user_ssh_keys(user.username)
        if not user_keys:
            raise Exception("User has not yet created a key -- instance cannot be launched")
        # FIXME: In a new PR, allow user to select the keypair for launching
        user_key = user_keys[0]
        ex_keyname = user_key.name
    return {"ex_metadata": ex_metadata, "ex_keyname": ex_keyname}


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

def update_instance_metadata(core_instance, data={}, replace=False):
    identity = core_instance.created_by_identity
    instance_id = core_instance.provider_alias
    esh_driver = get_cached_driver(identity=identity)
    esh_instance = esh_driver.get_instance(instance_id)
    return _update_instance_metadata(esh_driver, esh_instance, data, replace)

def _update_instance_metadata(esh_driver, esh_instance, data={}, replace=True):
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

    #if data.get('tmp_status') == '':
    #    raise Exception("There is a problem, houston")
    # ASSERT: We are ready to update the metadata
    if data.get('name'):
        esh_driver._connection.ex_set_server_name(esh_instance, data['name'])
    try:
        previous = esh_driver._connection.ex_get_metadata(esh_instance)
        current = esh_driver._connection.ex_write_metadata(
            esh_instance,
            data,
            replace_metadata=replace)
        logger.info("%s update_metadata: previous %s", esh_instance.id, previous)
        logger.info("%s update_metadata: data %s", esh_instance.id, data)
        logger.info("%s update_metadata: current %s", esh_instance.id, current)
        return current
    except Exception as e:
        logger.exception("Error updating the metadata")
        if 'incapable of performing the request' in e.message:
            return {}
        else:
            raise


def _create_and_attach_port(provider, driver, instance, core_identity):
    accounts = OSAccountDriver(core_identity.provider)
    tenant_id = instance.extra['tenantId']
    network_resources = accounts.network_manager.find_tenant_resources(
        tenant_id)
    network = network_resources['networks']
    subnet = network_resources['subnets']
    if not network or not subnet:
        network, subnet = accounts.create_network(core_identity)
    else:
        network = network[0]
        subnet = subnet[0]
    #    instance.id, network['id'], subnet['id'], new_fixed_ip, tenant_id)
    attached_intf = driver._connection.ex_attach_interface(
        instance.id,
        network['id'])
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
        raise Exception(
            "For this script, we need iptools. pip install iptools")
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


def _repair_instance_networking(
        esh_driver,
        esh_instance,
        provider_uuid,
        identity_uuid):
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
                    esh_driver.identity, str(core_identity.uuid), esh_instance.id)
    logger.info("Instance %s needs to hard reboot instead of resume" %
                esh_instance.id)
    esh_driver.reboot_instance(esh_instance, 'HARD')

    # Custom task-chain.. Wait for active then redeploy scripts
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
    final_update.pop('tmp_status', None)
    final_update.pop('iplant_suspend_fix', None)
    remove_status_task = update_metadata.si(
        esh_driver.__class__, esh_driver.provider, esh_driver.identity,
        esh_instance.id, final_update, replace_metadata=True)
    deploy_task.link(remove_status_task)

    # Attempt to redeploy after the restart..
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
        attachment_set = vol.extra.get('attachments', [])
        if not attachment_set:
            continue
        for attachment in attachment_set:
            if instance.alias == attachment['serverId']:
                raise VolumeAttachConflict(instance.alias, vol.alias)
    return False


def run_instance_volume_action(user, identity, esh_driver, esh_instance, action_type, action_params):
    from service import task
    provider_uuid = identity.provider.uuid
    identity_uuid = identity.uuid
    instance_id = esh_instance.alias
    volume_id = action_params.get('volume_id')
    mount_location = action_params.get('mount_location')
    device = action_params.get('device')
    if mount_location == 'null' or mount_location == 'None':
        mount_location = None
    if device == 'null' or device == 'None':
        device = None
    if 'attach_volume' == action_type:
        instance_status = esh_instance.extra.get('status', "N/A")
        if instance_status != 'active':
            raise VolumeAttachConflict(
                message='Instance %s must be active before attaching '
                'a volume. (Current: %s)'
                'Retry request when instance is active.'
                % (instance_id, instance_status))
        result = task.attach_volume_task(
                esh_driver, esh_instance.alias,
                volume_id, device, mount_location)
    elif 'mount_volume' == action_type:
        result = task.mount_volume_task(
                esh_driver, esh_instance.alias,
                volume_id, device, mount_location)
    elif 'unmount_volume' == action_type:
        (result, error_msg) =\
            task.unmount_volume_task(esh_driver,
                                     esh_instance.alias,
                                     volume_id, device,
                                     mount_location)
    elif 'detach_volume' == action_type:
        instance_status = esh_instance.extra['status']
        if instance_status not in ['suspended', 'active', 'shutoff']:
            raise VolumeDetachConflict(
                'Instance %s must be active, suspended, or stopped '
                'before detaching a volume. (Current: %s)'
                'Retry request when instance is active.'
                % (instance_id, instance_status))
        (result, error_msg) =\
            task.detach_volume_task(esh_driver,
                                    esh_instance.alias,
                                    volume_id)
        if not result and error_msg:
            # Return reason for failed detachment
            raise VolumeDetachConflict(error_msg)
    # Task complete, convert the volume and return the object
    esh_volume = esh_driver.get_volume(volume_id)
    core_volume = convert_esh_volume(esh_volume,
                                     provider_uuid,
                                     identity_uuid,
                                     user)
    return core_volume

def run_instance_action(user, identity, instance_id, action_type, action_params):
    """
    Dev Notes:
    Being used as the current 'interface' for running any InstanceAction
    for both API v1 and V2. We will look at how to 'generalize' this pattern later.
    """
    esh_driver = get_cached_driver(identity=identity)
    if not esh_driver:
        raise LibcloudInvalidCredsError("Driver could not be created")

    esh_instance = esh_driver.get_instance(instance_id)
    if not esh_instance:
        raise InstanceDoesNotExist(instance_id)

    if 'volume' in action_type:
        # Take care of volume actions separately
        result_obj = run_instance_volume_action(
            user, identity, esh_driver, esh_instance,
            action_type, action_params)
        return result_obj
    # Gather instance related parameters
    provider_uuid = identity.provider.uuid
    identity_uuid = identity.uuid
    logger.info("User %s has initiated instance action %s to be executed on Instance %s" % (user, action_type, instance_id))
    if 'resize' == action_type:
        size_alias = action_params.get('size', '')
        if isinstance(size_alias, int):
            size_alias = str(size_alias)
        result_obj = resize_instance(
            esh_driver, esh_instance, size_alias,
            provider_uuid, identity_uuid, user)
    elif 'confirm_resize' == action_type:
        result_obj = confirm_resize(
            esh_driver, esh_instance,
            provider_uuid, identity_uuid, user)
    elif 'revert_resize' == action_type:
        result_obj = esh_driver.revert_resize_instance(esh_instance)
    elif 'redeploy' == action_type:
        result_obj = redeploy_init(esh_driver, esh_instance, identity)
    elif 'resume' == action_type:
        result_obj = resume_instance(esh_driver, esh_instance,
                                     provider_uuid, identity_uuid,
                                     user)
    elif 'suspend' == action_type:
        result_obj = suspend_instance(esh_driver, esh_instance,
                                      provider_uuid, identity_uuid,
                                      user)
    elif 'shelve' == action_type:
        result_obj = shelve_instance(esh_driver, esh_instance,
                                     provider_uuid, identity_uuid,
                                     user)
    elif 'unshelve' == action_type:
        result_obj = unshelve_instance(esh_driver, esh_instance,
                                       provider_uuid, identity_uuid,
                                       user)
    elif 'shelve_offload' == action_type:
        result_obj = offload_instance(esh_driver, esh_instance)
    elif 'start' == action_type:
        result_obj = start_instance(
            esh_driver, esh_instance,
            provider_uuid, identity_uuid, user)
    elif 'stop' == action_type:
        result_obj = stop_instance(
            esh_driver, esh_instance,
            provider_uuid, identity_uuid, user)
    elif 'reset_network' == action_type:
        esh_driver.reset_network(esh_instance)
    elif 'console' == action_type:
        result_obj = esh_driver._connection\
                               .ex_vnc_console(esh_instance)
    elif 'reboot' == action_type:
        reboot_type = action_params.get('reboot_type', 'SOFT')
        result_obj = reboot_instance(esh_driver, esh_instance,
                                     identity_uuid, user, reboot_type)
    elif 'rebuild' == action_type:
        machine_alias = action_params.get('machine_alias', '')
        machine = esh_driver.get_machine(machine_alias)
        result_obj = esh_driver.rebuild_instance(esh_instance, machine)
    else:
        raise ActionNotAllowed(
            'Unable to to perform action %s.' % (action_type))
    return result_obj
