"""
Atmosphere service tasks methods

"""
from celery import chain

from threepio import logger

import service

from service.exceptions import DeviceBusyException

from service.tasks.driver import deploy_to, deploy_init_to, add_floating_ip
from service.tasks.driver import destroy_instance
from service.tasks.volume import attach_task, mount_task, check_volume_task
from service.tasks.volume import detach_task, umount_task


def deploy_init_task(driver, instance,
                     password=None, redeploy=False, *args, **kwargs):
    deploy_init_to.apply_async((driver.__class__,
                                driver.provider,
                                driver.identity,
                                instance.alias,
                                password,
                                redeploy),
                               immutable=True, countdown=60)


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
    destroy_instance.delay(identity_id,
                           instance.alias,
                           *args, **kwargs)


def detach_volume_task(driver, instance_id, volume_id, *args, **kwargs):
    #TODO: Handle the DeviceBusyException
    try:
        if hasattr(driver, 'deploy_to'):
            #Only attempt to umount if we have sh access
            umount_task.delay(
                driver.__class__, driver.provider, driver.identity,
                instance_id, volume_id).get()
        detach_task.delay(
            driver.__class__, driver.provider, driver.identity,
            instance_id, volume_id).get()
        return (True, None)
    except DeviceBusyException, dbe:
        return (False, dbe.message)


def attach_volume_task(driver, instance_id, volume_id, device=None,
                       mount_location=None, *args, **kwargs):
    logger.info("P_device - %s" % device)
    logger.info("P_mount_location - %s" % mount_location)
    attach_task.delay(
        driver.__class__, driver.provider, driver.identity,
        instance_id, volume_id, device).get()
    if not hasattr(driver, 'deploy_to'):
        #Do not attempt to mount if we don't have sh access
        return

    check_volume_task.delay(
        driver.__class__, driver.provider, driver.identity,
        instance_id, volume_id).get()
    mount_task.delay(
        driver.__class__, driver.provider, driver.identity,
        instance_id, volume_id, mount_location).get()
    return mount_location
