"""
Tasks for volume operations.
"""
from datetime import datetime

from celery.decorators import task
from celery.task import current
from celery import chain

from threepio import logger

from core.email import send_instance_email
from core.ldap import get_uid_number as get_unique_number
from core.models.instance import update_instance_metadata

from service.deploy import mount_volume, check_volume, mkfs_volume
from service.drivers.common import get_driver



@task(name="mount",
      max_retries=3,
      default_retry_delay=32,
      ignore_result=True)
def mount(driverCls, provider, identity, instance_id, volume_id, *args, **kwargs):
    try:
        logger.debug("mount task started at %s." % datetime.now())
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_id)
        volume = driver.get_volume(volume_id)
        device = volume.extra['attachmentSet'][0]['device']

        # check_volume (only if mount fails..)

        # logic for mount_location

        mv = mount_volume(device) # pass mount location

        kwargs.update({'deploy': mv})
        kwargs.update({'timeout': 120})
        private_key = "/opt/dev/atmosphere/extras/ssh/id_rsa"
        kwargs.update({'ssh_key': private_key})

        driver.deploy_to(instance, **kwargs)

        logger.debug("mount task finished at %s." % datetime.now())
    except Exception as exc:
        logger.warn(exc)
        mount.retry(exc=exc)


@task(name="umount",
      max_retries=3,
      default_retry_delay=32,
      ignore_result=True)
def umount(driverCls, provider, identity, instance, volume, *args, **kwargs):
    try:
        logger.debug("umount task started at %s." % datetime.now())
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_id)
        volume = driver.get_volume(volume_id)

        # TODO: Things
        # 

        logger.debug("umount task finished at %s." % datetime.now())
    except Exception as exc:
        logger.warn(exc)
        umount.retry(exc=exc)


@task(name="attach",
      default_retry_delay=20,
      ignore_result=True,
      max_retries=3)
def attach(driverCls, provider, identity, instance_id, device, *args, **kwargs):
    try:
        logger.debug("attach task started at %s." % datetime.now())
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_id)
        volume = driver.get_volume(volume_id)

        driver.attach_volume(instance,
                             volume,
                             device)

        # check_volume

        # if no fs: mkfs
        
        # mount

        logger.debug("attach task finished at %s." % datetime.now())
    except Exception as exc:
        logger.warn(exc)
        deploy_init_to.retry(exc=exc)


@task(name="deattach",
      max_retries=3,
      default_retry_delay=32,
      ignore_result=True)
def deattach(driverCls, provider, identity, instance, volume, *args, **kwargs):
    try:
        logger.debug("deattach task started at %s." % datetime.now())
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_id)
        volume = driver.get_volume(volume_id)

        # TODO: umount
        
        driver.destroy_volume(volume)

        logger.debug("deattach task finished at %s." % datetime.now())
    except Exception as exc:
        logger.warn(exc)
        deattach.retry(exc=exc)
