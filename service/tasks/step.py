"""
Tasks for step operations.
"""
#import re
#import time

from datetime import datetime

from celery.decorators import task
#from celery import chain

from threepio import logger
from rtwo.driver import EucaDriver, OSDriver

#from service.deploy import mount_volume, check_volume, mkfs_volume,\
#                           check_mount, umount_volume, lsof_location

from core.models.step import Step

from service.drivers.common import get_driver
#from service.exceptions import DeviceBusyException


@task(name="step_task",
      max_retries=2,
      default_retry_delay=20,
      ignore_result=False)
def step_task(driverCls, provider, identity, instance_id, step_id, *args, **kwargs):
    try:
        logger.debug("step task started at %s." % datetime.now())
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_id)
        step = Step.objects.get(id=step_id)

        private_key = "/opt/dev/atmosphere/extras/ssh/id_rsa"
        kwargs.update({'ssh_key': private_key})
        kwargs.update({'timeout': 120})
        script = step_script(step)
        kwargs.update({'deploy': script})

        driver.deploy_to(instance, **kwargs)

        logger.debug("step task finished at %s." % datetime.now())
    except Exception as exc:
        logger.warn(exc)
        step_task.retry(exc=exc)
