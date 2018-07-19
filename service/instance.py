import os.path
import time
import json
import uuid

from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django.utils.timezone import datetime

from celery.result import AsyncResult
from atmosphere.celery_init import app

from threepio import logger, status_logger

from rtwo.models.provider import AWSProvider, AWSUSEastProvider,\
    AWSUSWestProvider, EucaProvider,\
    OSProvider, OSValhallaProvider
from rtwo.exceptions import LibcloudBadResponseError
from rtwo.driver import OSDriver
from rtwo.drivers.openstack_user import UserManager
from rtwo.drivers.common import _token_to_keystone_scoped_project

from core.plugins import AllocationSourcePluginManager, EnforcementOverrideChoice
from service.driver import AtmosphereNetworkManager
from service.mock import AtmosphereMockNetworkManager

from rtwo.drivers.common import _connect_to_keystone_v3
from rtwo.drivers.openstack_network import NetworkManager
from rtwo.models.instance import MockInstance
from rtwo.models.machine import Machine
from rtwo.models.size import MockSize
from rtwo.models.volume import Volume
from rtwo.exceptions import LibcloudHTTPError  # Move into rtwo.exceptions later...
from libcloud.common.exceptions import BaseHTTPError  # Move into rtwo.exceptions later...

from core.query import only_current
from core.models.instance_source import InstanceSource
from core.models import AtmosphereUser, InstanceAllocationSourceSnapshot
from core.models.ssh_key import get_user_ssh_keys
from core.models.application import Application
from core.models.identity import Identity as CoreIdentity
from core.models.instance import Instance, convert_esh_instance, find_instance
from core.models.instance_action import InstanceAction
from core.models.size import convert_esh_size
from core.models.machine import ProviderMachine
from core.models.volume import convert_esh_volume
from core.models.provider import AccountProvider, Provider, ProviderInstanceAction
from core.exceptions import ProviderNotActive

from atmosphere import settings
from atmosphere.settings import secrets

from service.cache import get_cached_driver, invalidate_cached_instances
from service.driver import _retrieve_source, get_account_driver
from service.licensing import _test_license
from service.networking import get_topology_cls, ExternalRouter, ExternalNetwork, _get_unique_id
from service.exceptions import (
    OverAllocationError, AllocationBlacklistedError, OverQuotaError, SizeNotAvailable,
    HypervisorCapacityError, SecurityGroupNotCreated,
    VolumeAttachConflict, VolumeDetachConflict, UnderThresholdError, ActionNotAllowed,
    socket_error, ConnectionFailure, InstanceDoesNotExist, InstanceLaunchConflict, LibcloudInvalidCredsError,
    Unauthorized)

from service.accounts.openstack_manager import AccountDriver as OSAccountDriver

from neutronclient.common.exceptions import Conflict


def _get_size(esh_driver, esh_instance):
    if isinstance(esh_instance.size, MockSize) and \
        not isinstance(esh_instance, MockInstance):
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
        reboot_type="SOFT"):
    """
    Default to a soft reboot, but allow option for hard reboot.
    """
    from service.tasks.driver import wait_for_instance
    if reboot_type == "SOFT":
        _permission_to_act(identity_uuid, "Reboot")
    else:
        _permission_to_act(identity_uuid, "Hard Reboot")
    esh_driver.reboot_instance(esh_instance, reboot_type=reboot_type)
    driverCls = esh_driver.__class__
    provider = esh_driver.provider
    identity = esh_driver.identity
    wait_for_instance.delay(
        esh_instance.id, driverCls, provider, identity, "active")


def stop_instance(esh_driver, esh_instance, identity_uuid):
    from service.tasks.driver import wait_for_instance
    _permission_to_act(identity_uuid, "Stop")
    remove_floating_ip(esh_driver, esh_instance, identity_uuid)
    stopped = esh_driver.stop_instance(esh_instance)
    driverCls = esh_driver.__class__
    provider = esh_driver.provider
    identity = esh_driver.identity
    wait_for_instance.delay(
        esh_instance.id, driverCls, provider, identity, "shutoff")

def start_instance(esh_driver,
                   esh_instance,
                   identity_uuid,
                   user):
    from service.tasks.driver import deploy
    _permission_to_act(identity_uuid, "Start")
    restore_network(esh_driver, esh_instance, identity_uuid)
    driverCls = esh_driver.__class__
    provider = esh_driver.provider
    identity = esh_driver.identity
    esh_driver.start_instance(esh_instance)
    deploy_task = deploy.si(
        esh_driver.__class__,
        esh_driver.provider,
        esh_driver.identity,
        esh_instance.id,
        identity_uuid,
        user.username)
    deploy_task.delay()

def suspend_instance(esh_driver, esh_instance, identity_uuid, user):
    from service.tasks.driver import wait_for_instance
    _permission_to_act(identity_uuid, "Suspend")
    remove_floating_ip(esh_driver, esh_instance, identity_uuid)
    suspended = esh_driver.suspend_instance(esh_instance)
    driverCls = esh_driver.__class__
    provider = esh_driver.provider
    identity = esh_driver.identity
    wait_for_instance.delay(
        esh_instance.id, driverCls, provider, identity, "suspended")
    return suspended


def remove_floating_ip(esh_driver, esh_instance, core_identity_uuid):
    core_identity = CoreIdentity.objects.get(uuid=core_identity_uuid)
    network_driver = _to_network_driver(core_identity)
    network_driver.disassociate_floating_ip(esh_instance.id)


def restore_network(esh_driver, esh_instance, identity_uuid):
    core_identity = CoreIdentity.objects.get(uuid=identity_uuid)
    network = network_init(core_identity)
    return network


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


def _get_network_id(network_manager, esh_instance):
    """
    For a given instance, retrieve the network-name and
    convert it to a network-id
    """
    network_id = None

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


def redeploy_instance(
        esh_driver,
        esh_instance,
        core_identity,
        user):
    from service.tasks.driver import deploy
    from core.models.instance_history import InstanceStatusHistory
    core_instance = Instance.objects.get(provider_alias=esh_instance.id)

    # Each instance action must have an immediate effect on the status.
    # Openstack guarantees that after an action has successfully been received
    # the instance status will have a task/activity until the status proceeds
    # into a final state. Clients can use this test that an instance has a
    # pending activity to know to poll it. This ensures that after a
    # "redeploy" action the instance is immediately pollable.
    InstanceStatusHistory.update_history(core_instance, "deploying", "initializing")
    deploy.delay(
        esh_driver.__class__,
        esh_driver.provider,
        esh_driver.identity,
        esh_instance.id,
        core_identity.uuid,
        user.username)

def resume_instance(esh_driver,
                    esh_instance,
                    identity_uuid,
                    user):
    from service.tasks.driver import deploy
    _permission_to_act(identity_uuid, "Resume")
    restore_network(esh_driver, esh_instance, identity_uuid)
    driverCls = esh_driver.__class__
    provider = esh_driver.provider
    identity = esh_driver.identity
    deploy_task = deploy.si(
        driverCls,
        provider,
        identity,
        esh_instance.id,
        identity_uuid,
        user.username)
    resumed_instance = esh_driver.resume_instance(esh_instance)
    deploy_task.delay()


def shelve_instance(esh_driver,
                    esh_instance,
                    identity_uuid,
                    user):
    from service.tasks.driver import wait_for_instance
    _permission_to_act(identity_uuid, "Shelve")
    remove_floating_ip(esh_driver, esh_instance, identity_uuid)
    shelved = esh_driver._connection.ex_shelve_instance(esh_instance)
    driverCls = esh_driver.__class__
    provider = esh_driver.provider
    identity = esh_driver.identity
    wait_for_instance.delay(esh_instance.id, driverCls, provider, identity, ["shelved", "shelved_offloaded"])
    return shelved


def unshelve_instance(esh_driver,
                      esh_instance,
                      identity_uuid,
                      user):
    from service.tasks.driver import deploy
    _permission_to_act(identity_uuid, "Unshelve")
    driverCls = esh_driver.__class__
    provider = esh_driver.provider
    identity = esh_driver.identity
    deploy_task = deploy.si(
        driverCls, provider, identity, esh_instance.id, identity_uuid, user.username)
    restore_network(esh_driver, esh_instance, identity_uuid)
    unshelved = esh_driver._connection.ex_unshelve_instance(esh_instance)
    deploy_task.delay()


def offload_instance(esh_driver, esh_instance, identity_uuid, user):
    from service.tasks.driver import wait_for_instance
    _permission_to_act(identity_uuid, "Shelve Offload")
    remove_floating_ip(esh_driver, esh_instance, identity_uuid)
    offloaded = esh_driver._connection.ex_shelve_offload_instance(esh_instance)
    driverCls = esh_driver.__class__
    provider = esh_driver.provider
    identity = esh_driver.identity
    wait_for_instance.delay(esh_instance.id, driverCls, provider, identity, "shelved_offloaded")
    return offloaded


def destroy_instance(user, core_identity_uuid, instance_alias):
    success, esh_instance = _destroy_instance(
        core_identity_uuid, instance_alias)
    if not success and esh_instance:
        raise Exception("Instance could not be destroyed")
    os_cleanup_networking(core_identity_uuid)
    core_instance = find_instance(instance_alias)
    if not core_instance:
        raise Exception("Instance %s not found" % instance_alias)
    core_instance.end_date_all()
    return core_instance


def os_cleanup_networking(core_identity_uuid):
    from service.tasks.driver import clean_empty_ips
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


def _pre_launch_validation(
        username,
        esh_driver,
        identity_uuid,
        boot_source,
        size,
        allocation_source):
    """
    Used BEFORE launching a volume/instance .. Raise exceptions here to be dealt with by the caller.
    """
    identity = CoreIdentity.objects.get(uuid=identity_uuid)

    # May raise OverQuotaError
    check_quota(username, identity_uuid, size,
            include_networking=True)

    # May raise OverAllocationError, AllocationBlacklistedError
    check_allocation(username, allocation_source)

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
    provider = identity.provider
    if not provider.is_active():
        raise ProviderNotActive(provider)

    esh_driver = get_cached_driver(identity=identity)

    # May raise Exception("Volume/Machine not available")
    boot_source = get_boot_source(user.username, identity_uuid, source_alias)
    # May raise Exception("Size not available")
    size = check_size(esh_driver, size_alias, provider, boot_source)

    # Raise any other exceptions before launching here
    _pre_launch_validation(
        user.username,
        esh_driver,
        identity_uuid,
        boot_source,
        size,
        launch_kwargs.get('allocation_source'))

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
            esh_driver, user, identity, machine, size, name,
            deploy=deploy, **launch_kwargs)
    else:
        raise Exception("Boot source is of an unknown type")
    return core_instance


def boot_volume_instance(
        driver, user, identity, copy_source, size, name,
        # Depending on copy source, these specific kwargs may/may not be used.
        boot_index=0, shutdown=False, volume_size=None,
        # Other kwargs passed for future needs
        deploy=True, **kwargs):
    """
    Create a new volume and launch it as an instance
    """
    prep_kwargs, userdata, network = _pre_launch_instance(
        driver, user, identity, size, name, **kwargs)
    kwargs.update(prep_kwargs)
    instance, token, password = _boot_volume(
        driver, identity, copy_source, size,
        name, userdata, network, **prep_kwargs)
    return _complete_launch_instance(
        driver, identity, instance,
        user, token, password, deploy=deploy)


def launch_volume_instance(driver, user, identity, volume, size, name,
                           deploy=True, **kwargs):
    """
    Re-Launch an existing volume as an instance
    """
    prep_kwargs, userdata, network = _pre_launch_instance(
        driver, user, identity, size, name, **kwargs)
    kwargs.update(prep_kwargs)
    instance, token, password = _launch_volume(
        driver, identity, volume, size,
        name, userdata, network, **kwargs)
    return _complete_launch_instance(driver, identity, instance,
                                     user, token, password,
                                     deploy=deploy)


def launch_machine_instance(driver, user, identity, machine, size, name,
                            deploy=True, **kwargs):
    """
    Launch an existing machine as an instance
    """
    prep_kwargs, userdata, network = _pre_launch_instance(
        driver, user, identity, size, name, **kwargs)
    kwargs.update(prep_kwargs)
    instance, token, password = _launch_machine(
        driver, identity, machine, size,
        name, userdata, network, **kwargs)
    return _complete_launch_instance(driver, identity, instance,
                                     user, token, password,
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


def _launch_volume(driver, identity, volume, size, name, userdata_content, network,
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
                             ex_userdata=userdata_content, **kwargs)
    elif isinstance(driver.provider, AWSProvider):
        # TODO:Extra stuff needed for AWS provider here
        esh_instance = driver.deploy_instance(
            name=name, image=machine,
            size=size, deploy=True,
            token=token, **kwargs)
    else:
        raise Exception("Unable to launch with this provider.")
    return (esh_instance, token, password)


def _pre_launch_instance(driver, user, identity, size, name, **kwargs):
    """
    Returns:
    * Prep kwargs (username, password, token, & name)
    * User data (If Applicable)
    * LC Network (If Applicable)
    """
    prep_kwargs = _pre_launch_instance_kwargs(driver, identity, name)
    userdata = network = None
    if isinstance(driver.provider, OSProvider):
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


def _complete_launch_instance(
        driver,
        identity,
        instance,
        user,
        token,
        password,
        deploy=True):
    from service.tasks.driver import deploy_init_to
    # Create the Core/DB for instance
    core_instance = convert_esh_instance(
        driver, instance, identity.provider.uuid, identity.uuid,
        user, token, password)
    deploy_init_to.si(driver.__class__,
                                driver.provider,
                                driver.identity,
                                instance.alias,
                                identity,
                                user.username,
                                password,
                                deploy).apply_async(countdown=10)
    # Invalidate and return
    invalidate_cached_instances(identity=identity)
    return core_instance


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


def validate_size_fits_boot_source(esh_size, boot_source):
    disk_size = esh_size.disk
    if disk_size == 0 or boot_source.size_gb == 0:
        return
    if boot_source.size_gb > disk_size:
        raise SizeNotAvailable("Size Not Available. Disk is %s but image requires at least %s" % (disk_size, boot_source.size_gb))

def check_size(esh_driver, size_alias, provider, boot_source):
    try:
        esh_size = esh_driver.get_size(size_alias)
        if not convert_esh_size(esh_size, provider.uuid).active():
            raise SizeNotAvailable()
        if boot_source.is_machine():
            validate_size_fits_boot_source(esh_size, boot_source)
        return esh_size
    except LibcloudBadResponseError as bad_response:
        return _parse_libcloud_error(provider, bad_response)
    except LibcloudHTTPError as http_err:
        if http_err.code == 401:
            raise Unauthorized(http_err.message)
        raise ConnectionFailure(http_err.message)
    except Exception as exc:
        raise


def _parse_libcloud_error(provider, bad_response):
    """
    Parse a libcloud error to determine why calls failed (In this case, provider-specific errors).
    """
    msg = bad_response.body
    human_error = "Invalid response received from Provider: %s" % provider.location
    if "body: " in msg:
        raw_json = msg.split("body: ")[1]
        json_data = json.loads(raw_json)
        if "error" in json_data:
            json_data = json_data["error"]
        if "title" in json_data:
            human_error = json_data["title"]
        elif "message" in json_data:
            human_error = json_data["message"]
        else:
            human_error = json_data
    raise InstanceLaunchConflict("Provider %s returned unexpected error: %s" % (provider.location, human_error))


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
    application = app_version.application
    raise Exception(
        "Identity %s did not meet the requirements of the associated license on Application %s + Version %s" %
        (identity, application.name, app_version.name))


def check_allocation(username, allocation_source):
    logger.debug('check_allocation - username: %s', username)
    logger.debug('check_allocation - allocation_source: %s', allocation_source)
    user = AtmosphereUser.objects.filter(username=username).first()
    if not user:
        raise Exception("Username %s does not exist" % username)

    enforcement_override_choice = AllocationSourcePluginManager.get_enforcement_override(user,
                                                                                         allocation_source)
    logger.debug('check_allocation - enforcement_override_choice: %s', enforcement_override_choice)
    if enforcement_override_choice == EnforcementOverrideChoice.NEVER_ENFORCE:
        return
    elif enforcement_override_choice == EnforcementOverrideChoice.ALWAYS_ENFORCE:
        raise AllocationBlacklistedError(allocation_source.name)

    compute_remaining = allocation_source.time_remaining(user)
    over_allocation = compute_remaining < 0
    if over_allocation:
        raise OverAllocationError(allocation_source.name, abs(compute_remaining))


def check_quota(username, identity_uuid, esh_size,
        include_networking=False):
    from service.quota import check_over_instance_quota
    try:
        check_over_instance_quota(
            username, identity_uuid, esh_size,
            include_networking=include_networking)
    except ValidationError as bad_quota:
        raise OverQuotaError(message=bad_quota.message)


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
    security_group_name = core_identity.provider.get_config("network", "security_group_name", "default")
    if has_secret:
        return admin_security_group_init(core_identity)
    return user_security_group_init(core_identity, security_group_name = security_group_name)


def user_security_group_init(core_identity, security_group_name):
    network_driver = _to_network_driver(core_identity)
    user_neutron = network_driver.neutron
    extended_default_rules = _get_default_rules()
    user_security_group_rules = core_identity.provider.get_config('network', 'user_security_rules', extended_default_rules)
    security_group = get_or_create_security_group(security_group_name, user_neutron)
    neutron_set_security_group_rules(security_group_name, user_security_group_rules, user_neutron)
    return security_group


def _get_default_rules():
    """
    A basic set of rules:
    - Allow access to Port 22 (SSH)
    - Allow IPv4 Access
    - Allow IPv6 Access
    ---
    This is an EXAMPLE of what should be in your PROVIDER's `cloud_config`:
    cloud_config = {
        ...
        'network': {
            ...
            'user_security_rules': [
                {... rule1 ...},
                {... rule2 ...},
                {... rule3 ...}
            ],
            ...
        },
        ...
    }
    NOTE: new rules are DICTs and not 4-tuples!
    """
    extended_default_rules = [
        {
            "direction": "ingress",
            "ethertype": "IPv4",
        },
        {
            "direction": "ingress",
            "ethertype": "IPv6",
         },
        {
            "direction": "ingress",
            "port_range_min": 22,
            "port_range_max": 22,
            "protocol": "tcp",
            "remote_ip_prefix": "0.0.0.0/0",
         }
    ]
    return extended_default_rules


def neutron_set_security_group_rules(security_group_name, security_group_rules_dict, user_neutron):
    security_group = find_security_group(security_group_name, user_neutron)
    security_group_id = security_group[u'id']
    for sg_rule in security_group_rules_dict:
        try:
            rule_body = {"security_group_rule": {
                "direction": sg_rule['direction'],
                "port_range_min": sg_rule.get('port_range_min', None),
                "ethertype": sg_rule.get("ethertype", "IPv4"),
                "port_range_max": sg_rule.get('port_range_max', None),
                "protocol": sg_rule.get("protocol", None),
                "remote_group_id": security_group_id,
                "security_group_id": security_group_id
                 }
            }
            if 'remote_ip_prefix' in sg_rule:
                rule_body['security_group_rule']['remote_ip_prefix'] = sg_rule['remote_ip_prefix']
                rule_body['security_group_rule'].pop("remote_group_id")
            user_neutron.create_security_group_rule(body=rule_body)
        except Conflict:
            # The rule has already in the sec_group
            pass
    return True

def find_security_group(security_group_name, user_neutron):
    security_groups = user_neutron.list_security_groups()[u'security_groups']
    security_group = ''
    for sg in security_groups:
        if sg[u'name'] == security_group_name:
            security_group = sg
    if security_group != '':
        return security_group
    else:
        raise Exception('Could not find any existing security group')


def libcloud_set_security_group_rules(lc_driver, security_group, rules):
    """
    DEPRECATED: This legacy method was used to define security group rules as a 3/4-tuple
    For a more up-to-date method using neutron instead of libcloud, see neutron_set_security_group_rules.
    """
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


def get_or_create_security_group(security_group_name, user_neutron):
    security_group_list = user_neutron.list_security_groups()[u'security_groups']
    security_group = [sgroup for sgroup in security_group_list if sgroup[u'name'] == security_group_name]

    #sgroup_list = lc_driver.ex_list_security_groups()
    #security_group = [sgroup for sgroup in sgroup_list if sgroup.name == security_group_name]
    if len(security_group) > 0:
        security_group = security_group[0]
    else:
        body = {"security_group": {
            "name": security_group_name,
            "description": "Security Group created by Atmosphere"
             }
        }
        security_group = user_neutron.create_security_group(body=body)

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
    has_secret = core_identity.get_credential('secret') is not None
    if has_secret:
        return admin_keypair_init(core_identity)
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
    topology_name = core_identity.provider.get_config('network', 'topology', 'External Router Topology')
    if not topology_name or topology_name == "External Router Topology":
        return admin_network_init(core_identity)  # NOTE: This flow *ONLY* works with external router.
    return user_network_init(core_identity)


def _to_network_driver(core_identity):
    provider_type = core_identity.provider.type.name
    if provider_type == 'mock':
         return AtmosphereMockNetworkManager.create_manager(core_identity)
    return AtmosphereNetworkManager.create_manager(core_identity)


def _to_user_driver(core_identity):
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
        user_driver = UserManager(auth_url=auth_url,
                                  auth_token=auth_token,
                                  project_name=project_name,
                                  domain_name=domain_name,
                                  session=sess,
                                  version="v3")
    else:
        username = all_creds['key']
        password = all_creds['secret']
        (auth, sess, token) = _connect_to_keystone_v3(
            auth_url, username, password,
            project_name, domain_name)
        user_driver = UserManager(auth_url=auth_url,
                                  username=username,
                                  password=password,
                                  project_name=project_name,
                                  domain_name=domain_name,
                                  session=sess,
                                  version="v3")
    return user_driver


def user_network_init(core_identity):
    """
    WIP -- need to figure out how to do this within the scope of libcloud // OR using existing authtoken to connect with neutron.
    """
    provider_type = core_identity.provider.type.name
    if provider_type == 'mock':
        return _to_network_driver(core_identity)
    username = core_identity.get_credential('key')
    if not username:
        username = core_identity.created_by.username
    esh_driver = get_cached_driver(identity=core_identity)
    dns_nameservers = core_identity.provider.get_config('network', 'dns_nameservers', [])
    subnet_pool_id = core_identity.provider.get_config('network', 'subnet_pool_id', raise_exc=False)
    topology_name = core_identity.provider.get_config('network', 'topology', raise_exc=False)
    if not topology_name:
        logger.error(
            "Network topology not selected -- "
            "Will attempt to use the last known default: ExternalRouter.")
        topology_name = "External Router Topology"
    dns_nameservers = core_identity.provider.get_config('network', 'dns_nameservers', [])
    network_driver = _to_network_driver(core_identity)
    user_neutron = network_driver.neutron
    network_strategy = initialize_user_network_strategy(
        topology_name, core_identity, network_driver, user_neutron)
    network_resources = network_strategy.create(
        username=username, dns_nameservers=dns_nameservers, subnet_pool_id=subnet_pool_id)
    network_strategy.post_create_hook(network_resources)
    return network_resources


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
    provider_type = core_identity.provider.type.name
    if provider_type == 'mock':
        return _to_network_driver(core_identity)
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
    security_group_name = core_identity.provider.get_config("network", "security_group_name", "default")
    return {"ex_metadata": ex_metadata, "ex_keyname": ex_keyname}


def run_instance_volume_action(user, identity, esh_driver, esh_instance, action_type, action_params):
    from service import task
    provider_uuid = identity.provider.uuid
    identity_uuid = identity.uuid
    instance_id = esh_instance.alias
    volume_id = action_params.get('volume_id')
    mount_location = action_params.get('mount_location')

    # TODO: We are taking 'device' as a param
    # but we don't *need* to. volume_id will provide this for us.
    # Remove this param (and comment) in the future...
    device_location= action_params.get('device')
    if device_location == 'null' or device_location == 'None':
        device_location = None

    if mount_location == 'null' or mount_location == 'None':
        mount_location = None
    if 'attach_volume' == action_type:
        instance_status = esh_instance.extra.get('status', "N/A")
        if instance_status != 'active':
            raise VolumeAttachConflict(
                message='Instance %s must be active before attaching '
                'a volume. (Current: %s)'
                'Retry request when instance is active.'
                % (instance_id, instance_status))
        result = task.attach_volume(
                identity, esh_driver, esh_instance.alias,
                volume_id, device_location, mount_location)
    elif 'mount_volume' == action_type:
        result = task.mount_volume(
                identity, esh_driver, esh_instance.alias,
                volume_id, device_location, mount_location)
    elif 'unmount_volume' == action_type:
        (result, error_msg) =\
            task.unmount_volume(esh_driver,
                                     esh_instance.alias,
                                     volume_id, device_location,
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
            task.detach_volume(esh_driver,
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

    # NOTE: This metadata statement is a HACK! It should be removed when all instances matching this metadata key have been removed.
    instance_has_home_mount = esh_instance.extra['metadata'].get('atmosphere_ephemeral_home_mount', 'false').lower()
    if instance_has_home_mount == 'true' and action_type == 'shelve':
        logger.info("Instance %s will be suspended instead of shelved, because the ephemeral storage is in /home", esh_instance.id)
        action_type = 'suspend'

    logger.info("User %s has initiated instance action %s to be executed on Instance %s" % (user, action_type, instance_id))
    if action_type in ('start', 'resume', 'unshelve'):
        logger.info('Going to check the allocation of the instance due to the action type: %s', action_type)
        allocation_snapshot = InstanceAllocationSourceSnapshot.objects.get(instance__provider_alias=instance_id)
        allocation = allocation_snapshot.allocation_source
        check_allocation(user.username, allocation)
    if 'redeploy' == action_type:
        result_obj = redeploy_instance(esh_driver, esh_instance, identity, user=user)
    elif 'resume' == action_type:
        result_obj = resume_instance(esh_driver, esh_instance, identity_uuid, user)
    elif 'suspend' == action_type:
        result_obj = suspend_instance(esh_driver, esh_instance, identity_uuid, user)
    elif 'shelve' == action_type:
        result_obj = shelve_instance(esh_driver, esh_instance, identity_uuid, user)
    elif 'unshelve' == action_type:
        result_obj = unshelve_instance(esh_driver, esh_instance, identity_uuid, user)
    elif 'shelve_offload' == action_type:
        result_obj = offload_instance(esh_driver, esh_instance, identity_uuid, user)
    elif 'start' == action_type:
        result_obj = start_instance(
            esh_driver, esh_instance, identity_uuid, user)
    elif 'stop' == action_type:
        result_obj = stop_instance(esh_driver, esh_instance, identity_uuid)
    elif 'reboot' == action_type:
        reboot_type = action_params.get('reboot_type', 'SOFT')
        result_obj = reboot_instance(esh_driver, esh_instance, identity_uuid, reboot_type)
    else:
        raise ActionNotAllowed(
            'Unable to to perform action %s.' % (action_type))

    update_status(
        esh_driver,
        esh_instance.id,
        provider_uuid,
        identity_uuid,
        user)
    invalidate_cached_instances(
        identity=CoreIdentity.objects.get(
            uuid=identity_uuid))

    if result_obj == AsyncResult:
        return str(result_obj)
    return result_obj
