"""
Atmosphere service tasks methods

"""
from threepio import logger

from service.tasks.driver import deploy_to,\
    deploy_init_to, add_floating_ip, destroy_instance
from service.tasks.volume import detach_task, attach_task

def deploy_init_task(driver, instance, *args, **kwargs):
    deploy_init_to.apply_async((driver.__class__,
                                driver.provider,
                                driver.identity,
                                instance.alias),
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


def destroy_instance_task(driver, instance, *args, **kwargs):
    destroy_instance.delay(driver.__class__,
                           driver.provider,
                           driver.identity,
                           instance.alias,
                           *args, **kwargs)


def detach_volume_task(driver, instance_id, volume_id, *args, **kwargs):
    #TODO: Handle the DeviceBusyException
    async_task = detach_task.delay(
        driver.__class__, driver.provider, driver.identity,
        instance_id, volume_id, *args, **kwargs)
    async_task.wait()




def attach_volume_task(driver, instance_id, volume_id, device=None, *args, **kwargs):
    #TODO: Include the volume mount_location in data
    async_task = attach_task.delay(
        driver.__class__, driver.provider, driver.identity,
        instance_id, volume_id, device, *args, **kwargs)
    async_task.wait()




