"""
Atmosphere service tasks methods

"""
from celery import chain

from threepio import logger

import service

from service.exceptions import DeviceBusyException, VolumeMountConflict

from service.tasks.driver import deploy_to, deploy_init_to, add_floating_ip
from service.tasks.driver import destroy_instance
from service.tasks.volume import attach_task, mount_task, check_volume_task
from service.tasks.volume import detach_task, umount_task,\
        mount_failed
from service.tasks.volume import update_volume_metadata, update_mount_location


def deploy_init_task(driver, instance,
                     username=None, password=None, token=None, redeploy=False,
                     *args, **kwargs):
    from service.tasks.driver import _update_status_log
    _update_status_log(instance, "Launching Instance")
    deploy_init_to.apply_async((driver.__class__,
                                driver.provider,
                                driver.identity,
                                instance.alias,
                                token,
                                redeploy),
                               immutable=True, countdown=20)


def deploy_to_task(driver, instance, *args, **kwargs):
    deploy_to.delay(driver.__class__,
                    driver.provider,
                    driver.identity,
                    instance.alias,
                    *args, **kwargs)


def add_floating_ip_task(driver, instance, *args, **kwargs):
    add_floating_ip.delay(driver.__class__,
                          driver.provider,
                          driver.identity,
                          instance.alias,
                          *args, **kwargs)


def destroy_instance_task(instance, identity_id, *args, **kwargs):
    return destroy_instance.delay(
            instance.alias, identity_id, *args, **kwargs)


def detach_volume_task(driver, instance_id, volume_id, *args, **kwargs):
    try:
        detach_volume = detach_task.si(
            driver.__class__, driver.provider, driver.identity,
            instance_id, volume_id)
        if not hasattr(driver, 'deploy_to'):
            detach_volume.apply_async()
            return (True, None)
        #Only attempt to umount if we have sh access
        umount_chain = _get_umount_chain(driver, instance_id, volume_id, detach_volume)
        umount_chain.apply_async()
        return (True, None)
    except Exception, exc:
        return (False, exc.message)


def attach_volume_task(driver, instance_id, volume_id, device=None,
                       mount_location=None, *args, **kwargs):
    """
    Attach (And mount, if possible) volume to instance
    Device and mount_location assumed if empty
    """
    logger.info("Attach: %s --> %s" % (volume_id,instance_id))
    logger.info("device_location:%s, mount_location: %s"
            % (device, mount_location))
    try:
        attach_volume = attach_task.si(
            driver.__class__, driver.provider, driver.identity,
            instance_id, volume_id, device)
        if not hasattr(driver, 'deploy_to'):
            #Do not attempt to mount if we don't have sh access
            attach_volume.apply_async()
            #No mount location, return None
            return None
        mount_chain = _get_mount_chain(driver, instance_id, volume_id,
                device, mount_location)
        attach_volume.link(mount_chain)
        attach_volume.apply_async()
    except Exception, e:
        raise VolumeMountConflict(instance_id, volume_id)
    return mount_location

def _get_umount_chain(driver, instance_id, volume_id, detach_task):
    driverCls = driver.__class__
    provider = driver.provider
    identity = driver.identity
    pre_umount_status = update_volume_metadata.si(
            driverCls, provider, identity,
            volume_id, {'tmp_status':'unmounting'})
    umount= umount_task.si(
            driver.__class__, driver.provider, driver.identity,
            instance_id, volume_id)
    post_umount_status = update_volume_metadata.si(
            driverCls, provider, identity,
            volume_id, {'tmp_status':'',
                        'mount_location':''})

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
    post_umount_status.link(detach_task)
    return pre_umount_status

def _get_mount_chain(driver, instance_id, volume_id, device, mount_location):
    driverCls = driver.__class__
    provider = driver.provider
    identity = driver.identity

    pre_mount_status = update_volume_metadata.si(
            driverCls, provider, identity,
            volume_id, {'tmp_status':'mounting'})
    pre_mount = check_volume_task.si(
        driverCls, provider, identity,
        instance_id, volume_id)
    mount = mount_task.si(
            driverCls, provider, identity,
            instance_id, volume_id, device, mount_location)
    post_mount = update_mount_location.s(
            driverCls, provider, identity, volume_id)
    post_mount_status = update_volume_metadata.si(
            driverCls, provider, identity,
            volume_id, {'tmp_status':''})
    #Error Links
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
    #Return the head node
    return pre_mount_status

