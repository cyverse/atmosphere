"""
Atmosphere service tasks methods

"""
from threepio import logger

from service.tasks.driver import deploy_to,\
    deploy_init_to, add_floating_ip, destroy_instance


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
