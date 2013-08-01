"""
Tasks for volume operations.
"""
import re

from datetime import datetime

from celery.decorators import task
from celery.task import current
from celery import chain

from threepio import logger

from core.email import send_instance_email
from core.ldap import get_uid_number as get_unique_number
from core.models.instance import update_instance_metadata

from service.deploy import mount_volume, check_volume, mkfs_volume,\
                           check_mount, umount_volume, lsof_location

from service.drivers.common import get_driver
from service.exceptions import DeviceBusyException

@task(name="check_volume_task",
      max_retries=3,
      default_retry_delay=32,
      ignore_result=True)
def check_volume_task(driverCls, provider, identity, instance, volume, *args, **kwargs):
    try:
        logger.debug("check_volume task started at %s." % datetime.now())
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_id)
        volume = driver.get_volume(volume_id)
        device = volume.extra['attachmentSet'][0]['device']

        kwargs.update({'timeout': 120})
        private_key = "/opt/dev/atmosphere/extras/ssh/id_rsa"
        kwargs.update({'ssh_key': private_key})

        cv_script = check_volume(device)
        kwargs.update({'deploy': cv_script})
        driver.deploy_to(instance, **kwargs)
        #Script execute

        if cv_script.exit_status != 0:
            if 'No such file' in cv_script.stdout:
                raise Exception('Volume check failed: Device %s does not exist on instance %s' %
                        (device,instance))
            elif 'Bad magic number' in cv_script.stdout:
                #Filesystem needs to be created for this device
                logger.info("Mkfs needed")
                mkfs_script = mkfs_volume(device)
                kwargs.update({'deploy': mkfs_script})
                driver.deploy_to(instance, **kwargs)
            else:
                raise Exception('Volume check failed: Something weird')

        logger.debug("check_volume task finished at %s." % datetime.now())
    except Exception as exc:
        logger.warn(exc)
        check_volume_task.retry(exc=exc)


@task(name="mount",
      max_retries=3,
      default_retry_delay=32,
      ignore_result=True)
def mount_task(driverCls, provider, identity, instance_id, volume_id,
               mount_location=None, *args, **kwargs):
    try:
        logger.debug("mount task started at %s." % datetime.now())
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_id)
        volume = driver.get_volume(volume_id)
        device = volume.extra['attachmentSet'][0]['device']
        
        check_volume_task.si(driverCls, provider, identity, instance_id,
                                volume_id, *args, **kwargs)


        private_key = "/opt/dev/atmosphere/extras/ssh/id_rsa"
        kwargs.update({'ssh_key': private_key})
        kwargs.update({'timeout': 120})

        cm_script = check_mount()
        kwargs.update({'deploy': cm_script})
        driver.deploy_to(instance, **kwargs)

        #Occurs when device has already been mounted
        if device in cm_script.stdout:
            return
        
        if not mount_location:
            inc = 1
            while True:
                if '/vol%s' % inc in cm_script.stdout:
                    inc += 1
                else:
                    break
            mount_location = '/vol%s' % inc

        mv_script = mount_volume(device, mount_location)
        kwargs.update({'deploy': mv_script})
        driver.deploy_to(instance, **kwargs)

        logger.debug("mount task finished at %s." % datetime.now())
    except Exception as exc:
        logger.warn(exc)
        mount_task.retry(exc=exc)


@task(name="umount_task",
      max_retries=3,
      default_retry_delay=32,
      ignore_result=True)
def umount_task(driverCls, provider, identity, instance_id, volume_id, *args, **kwargs):
    try:
        logger.debug("umount task started at %s." % datetime.now())
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_id)
        volume = driver.get_volume(volume_id)
        device = volume.extra['attachmentSet'][0]['device']

        #Check mount to find the mount_location for device
        private_key = "/opt/dev/atmosphere/extras/ssh/id_rsa"
        kwargs.update({'ssh_key': private_key})
        kwargs.update({'timeout': 120})

        mount_location = None
        cm_script = check_mount()
        kwargs.update({'deploy': cm_script})
        driver.deploy_to(instance, **kwargs)
        regex = re.compile("(?P<device>[\w/]+) on (?P<location>.*) type")
        for line in cm_script.stdout.split('\n'):
            res = regex.search(line)
            if not res:
                continue
            search_dict = res.groupdict()
            dev_found = search_dict['device']
            if device == dev_found:
                mount_location = search_dict['location']
                break
        #Volume not mounted, move along..
        if not mount_location:
            return

        um_script = umount_volume(device)
        kwargs.update({'deploy': um_script})
        driver.deploy_to(instance, **kwargs)

        if 'device is busy' in um_script.stdout:
            #Show all processes that are making device busy..
            lsof_script = lsof_location(mount_location)
            kwargs.update({'deploy': lsof_script})
            driver.deploy_to(instance, **kwargs)

            regex = re.compile("(?P<name>[\w]+)\s*(?P<pid>[\d]+)")
            offending_processes = []
            for line in lsof_script.stdout.split('\n'):
                res = regex.search(line)
                if not res:
                    continue
                search_dict = res.groupdict()
                offending_processes.append(
                    (search_dict['name'],search_dict['pid']))

            raise DeviceBusyException(offending_processes)
        #Return here if no errors occurred..
        logger.debug("umount task finished at %s." % datetime.now())
    except DeviceBusyException:
        raise
    except Exception as exc:
        logger.warn(exc)
        umount_task.retry(exc=exc)


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
