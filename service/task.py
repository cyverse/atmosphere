"""
Atmosphere service tasks methods

"""
from celery import chain

from threepio import logger

from service.exceptions import DeviceBusyException, VolumeMountConflict, InstanceDoesNotExist

from service.tasks.driver import deploy_init_to
from service.tasks.driver import destroy_instance
from service.tasks.volume import attach_task, mount_volume_task, check_volume_task
from service.tasks.volume import detach_task, unmount_volume_task,\
    mount_failed
from service.tasks.volume import update_volume_metadata, update_mount_location


def print_task_chain(start_link):
    """
    Prints a chain of 'link' methods.. Useful for debugging!
    """
    next_link = start_link
    while next_link.options.get('link'):
        if start_link == next_link:
            print next_link.values()[1],
        next_link = next_link.options['link'][0]
        print "--> %s" % next_link.values()[1],

# Instance-specific tasks


def deploy_init_task(driver, instance, identity,
                     username=None, password=None, token=None,
                     redeploy=False, deploy=True, *args, **kwargs):
    from service.tasks.driver import _update_status_log
    _update_status_log(instance, "Launching Instance")
    logger.debug("deploy_init_task redeploy = %s" % redeploy)
    return deploy_init_to.apply_async((driver.__class__,
                                driver.provider,
                                driver.identity,
                                instance.alias,
                                identity,
                                username,
                                password,
                                redeploy,
                                deploy),
                               immutable=True)


def destroy_instance_task(user, instance, identity_uuid, *args, **kwargs):
    if not instance:
        raise InstanceDoesNotExist()
    return destroy_instance.delay(
        instance.alias, user, identity_uuid, *args, **kwargs)

# Volume-specific task-callers


def attach_volume(core_identity, driver, instance_id, volume_id, device_location=None,
                       mount_location=None, *args, **kwargs):
    """
    Attach (And mount, if possible) volume to instance
    device_location and mount_location assumed if empty
    """
    logger.info("Attach: %s --> %s" % (volume_id, instance_id))
    logger.info("device_location:%s, mount_location: %s"
                % (device_location, mount_location))
    try:
        init_task = attach_task.si(
            driver.__class__, driver.provider, driver.identity,
            instance_id, volume_id, device_location)
        mount_chain = _get_mount_chain(core_identity, driver, instance_id, volume_id,
                                       device_location, mount_location)
        init_task.link(mount_chain)
        print_task_chain(init_task)
        init_task.apply_async()
    except Exception as e:
        raise VolumeMountConflict(instance_id, volume_id)
    return mount_location


def detach_volume(driver, instance_id, volume_id, *args, **kwargs):
    try:
        detach = detach_task.si(
            driver.__class__, driver.provider, driver.identity,
            instance_id, volume_id)
        # Only attempt to umount if we have sh access
        init_task = _get_umount_chain(
            driver,
            instance_id,
            volume_id,
            detach)
        print_task_chain(init_task)
        init_task.apply_async()
        return (True, None)
    except Exception as exc:
        return (False, exc.message)


def unmount_volume(driver, instance_id, volume_id, *args, **kwargs):
    """
    This task-caller will:
    - verify that volume is attached
    - raise exceptions that can be handled _prior_ to running async tasks
    - create an async "task chain" and execute if all pre-conditions are met.
    """
    try:
        logger.info("UN-Mount ONLY: %s --> %s" % (volume_id, instance_id))
        # Only attempt to umount if we have sh access
        vol = driver.get_volume(volume_id)
        if not driver._connection.ex_volume_attached_to_instance(
                vol,
                instance_id):
            raise VolumeMountConflict("Cannot unmount volume %s "
                                      "-- Not attached to instance %s"
                                      % (volume_id, instance_id))
        unmount_chain = _get_umount_chain(driver, instance_id, volume_id)
        unmount_chain.apply_async()
        return (True, None)
    except Exception as exc:
        logger.exception("Exception occurred creating the unmount task")
        return (False, exc.message)


def mount_volume(core_identity, driver, instance_id, volume_id, device=None,
                      mount_location=None, *args, **kwargs):
    """
    This task-caller will:
    - verify that volume is not already mounted
    - raise exceptions that can be handled _prior_ to running async tasks
    - create an async "task chain" and execute if all pre-conditions are met.
    """
    logger.info("Mount ONLY: %s --> %s" % (volume_id, instance_id))
    logger.info("device_location:%s --> mount_location: %s"
                % (device, mount_location))
    try:
        vol = driver.get_volume(volume_id)
        existing_mount = vol.extra.get('metadata', {}).get('mount_location')
        if existing_mount:
            raise VolumeMountConflict(
                instance_id,
                volume_id,
                "Volume already mounted at %s. Run 'unmount_volume' first!" %
                existing_mount)
        if not driver._connection.ex_volume_attached_to_instance(
                vol,
                instance_id):
            raise VolumeMountConflict(
                instance_id, volume_id, "Cannot mount volume %s "
                "-- Not attached to instance %s" %
                (volume_id, instance_id))
        mount_chain = _get_mount_chain(core_identity, driver, instance_id, volume_id,
                                       device, mount_location)
        mount_chain.apply_async()
    except VolumeMountConflict:
        raise
    except Exception as e:
        logger.exception("Exc occurred")
        raise VolumeMountConflict(instance_id, volume_id)
    return mount_location

# "Chain builders" -- called by task callers above


def _get_umount_chain(driver, instance_id, volume_id, detach_task=None):
    driverCls = driver.__class__
    provider = driver.provider
    identity = driver.identity
    pre_umount_status = update_volume_metadata.si(
        driverCls, provider, identity,
        volume_id, {'tmp_status': 'unmounting'})
    umount = unmount_volume_task.si(
        driver.__class__, driver.provider, driver.identity,
        instance_id, volume_id)
    post_umount_status = update_volume_metadata.si(
        driverCls, provider, identity,
        volume_id, {'tmp_status': '',
                    'mount_location': ''})

    pre_umount_status.link_error(
        mount_failed.s(
            driverCls, provider, identity, volume_id, True))
    umount.link_error(
        mount_failed.s(
            driverCls, provider, identity, volume_id, True))
    post_umount_status.link_error(
        mount_failed.s(
            driverCls, provider, identity, volume_id, True))
    pre_umount_status.link(umount)
    umount.link(post_umount_status)
    if detach_task:
        post_umount_status.link(detach_task)
    return pre_umount_status


def _get_mount_chain(core_identity, driver, instance_id, volume_id, device_location, mount_location):
    driverCls = driver.__class__
    provider = driver.provider
    identity = driver.identity
    core_provider = core_identity.provider
    fs_type = core_provider.get_config("deploy", "volume_fs_type", "ext4")
    mount_prefix = core_provider.get_config("deploy", "volume_mount_prefix", "/vol_")
    pre_mount_status = update_volume_metadata.si(
        driverCls, provider, identity,
        volume_id, {'tmp_status': 'mounting'})
    pre_mount = check_volume_task.si(
        driverCls, provider, identity,
        instance_id, volume_id, fs_type)
    mount = mount_volume_task.si(
        driverCls, provider, identity,
        instance_id, volume_id, device_location, mount_location, fs_type,
        mount_prefix=mount_prefix)
    post_mount = update_mount_location.s(
        driverCls, provider, identity, volume_id)
    post_mount_status = update_volume_metadata.si(
        driverCls, provider, identity,
        volume_id, {'tmp_status': ''})
    # Error Links
    pre_mount_status.link_error(
        mount_failed.s(
            driverCls, provider, identity, volume_id))
    pre_mount.link_error(
        mount_failed.s(
            driverCls, provider, identity, volume_id))
    mount.link_error(
        mount_failed.s(
            driverCls, provider, identity, volume_id))
    post_mount.link_error(
        mount_failed.s(
            driverCls, provider, identity, volume_id))
    post_mount_status.link_error(
        mount_failed.s(
            driverCls, provider, identity, volume_id))
    # Make a chain with link
    pre_mount_status.link(pre_mount)
    pre_mount.link(mount)
    mount.link(post_mount)
    post_mount.link(post_mount_status)
    # Return the head node
    return pre_mount_status
