"""
Atmosphere service tasks methods

"""
from threepio import logger

from service.tasks.driver import deploy_to,\
    deploy_init_to, add_floating_ip, destroy_instance
from service.tasks.volume import detach_task, attach_task
from service.exceptions import DeviceBusyException
import service

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
    try:
        async_task = detach_task.delay(
            driver.__class__, driver.provider, driver.identity,
            instance_id, volume_id, *args, **kwargs)
        async_task.wait()
        return (True, None)
    except service.exceptions.DeviceBusyException, dbe:
        return (False, dbe.message)
    except DeviceBusyException, dbe:
        return (False, dbe.message)





def attach_volume_task(driver, instance_id, volume_id, device=None,
        mount_location=None, *args, **kwargs):
    #TODO: Include the volume mount_location in data
    async_task = attach_task.delay(
        driver.__class__, driver.provider, driver.identity,
        instance_id, volume_id, device, mount_location, *args, **kwargs)
    #async_task.wait()




