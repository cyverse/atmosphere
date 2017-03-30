"""
Tasks for volume operations.
"""
import re
import time

from datetime import datetime

from celery import current_app as app
from celery.result import allow_join_result
from celery.decorators import task
from celery import chain

from threepio import celery_logger
from rtwo.driver import EucaDriver, OSDriver
from rtwo.exceptions import LibcloudDeploymentError

from atmosphere.settings.local import ATMOSPHERE_PRIVATE_KEYFILE

from service.driver import get_driver
from service.deploy import (
    mount_volume,
    check_mount, umount_volume, lsof_location,
    deploy_check_volume, deploy_mount_volume,
    build_host_name, execution_has_failures, execution_has_unreachable)
from service.exceptions import DeviceBusyException


@task(name="check_volume_task",
      max_retries=0,
      default_retry_delay=20,
      ignore_result=False)
def check_volume_task(driverCls, provider, identity,
                      instance_id, volume_id, device_type='ext4', *args, **kwargs):
    try:
        celery_logger.debug("check_volume task started at %s." % datetime.now())
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_id)
        volume = driver.get_volume(volume_id)
        username = identity.get_username()
        attach_data = volume.extra['attachments'][0]
        device_location = attach_data['device']
        celery_logger.info("device_location: %s" % device_location)

        # One playbook to make two checks:
        # 1. Voume exists
        # 2. Volume has a filesystem
        #    (If not, create one of type 'device_type')
        playbooks = deploy_check_volume(
            instance.ip, username, instance.id,
            device_location, device_type=device_type)
        celery_logger.info(playbooks.__dict__)
        hostname = build_host_name(instance.id, instance.ip)
        result = False if execution_has_failures(playbooks, hostname)\
            or execution_has_unreachable(playbooks, hostname) else True
        if not result:
            raise Exception(
                "Error encountered while checking volume for filesystem: %s"
                % playbooks.stats.summarize(host=hostname))
        return result
    except LibcloudDeploymentError as exc:
        celery_logger.exception(exc)
    except Exception as exc:
        celery_logger.warn(exc)
        check_volume_task.retry(exc=exc)


def _parse_mount_location(mount_output, device_location):
    """
    GENERAL ASSUMPTION:
    Mount output is ALWAYS the same, and it looks like this:
    <DEV_LOCATION> on <MOUNT_LOCATION> type (Disk Specs ...)
    By splitting ' on '     AND      ' type '
    we can always retrieve <MOUNT_LOCATION>
    """
    for line in mount_output.split("\n"):
        if device_location not in line:
            continue
        before_text_idx = line.find(" on ") + 4
        after_text_idx = line.find(" type ")
        if before_text_idx == -1 or after_text_idx == -1:
            return ""
        return line[before_text_idx:after_text_idx]


@task(name="mount_task",
      max_retries=0,
      default_retry_delay=20,
      ignore_result=False)
def mount_task(driverCls, provider, identity, instance_id, volume_id,
               device_location, mount_location, device_type,
               mount_prefix=None, *args, **kwargs):
    try:
        celery_logger.debug("mount task started at %s." % datetime.now())
        celery_logger.debug("mount_location: %s" % (mount_location, ))
        driver = get_driver(driverCls, provider, identity)
        username = identity.get_username()
        instance = driver.get_instance(instance_id)
        volume = driver.get_volume(volume_id)

        try:
            attach_data = volume.extra['attachments'][0]
            if not device_location:
                device_location = attach_data['device']
        except (KeyError, IndexError):
            celery_logger.warn("Volume %s missing attachments in Extra"
                               % (volume,))
        if not device_location:
            raise Exception("No device_location found or inferred by volume %s" % volume)
        if not mount_prefix:
            mount_prefix = "/vol_"

        last_char = device_location[-1]  # /dev/sdb --> b
        if not mount_location:
            mount_location = mount_prefix + last_char

        playbooks = deploy_mount_volume(
            instance.ip, username, instance.id,
            device_location, mount_location=mount_location, device_type=device_type)
        celery_logger.info(playbooks.__dict__)
        hostname = build_host_name(instance.id, instance.ip)
        result = False if execution_has_failures(playbooks, hostname)\
            or execution_has_unreachable(playbooks, hostname) else True
        if not result:
            raise Exception(
                "Error encountered while mounting volume: %s"
                % playbooks.stats.summarize(host=hostname))
        return mount_location
    except Exception as exc:
        celery_logger.warn(exc)
        mount_task.retry(exc=exc)


@task(name="umount_task",
      max_retries=3,
      default_retry_delay=32,
      ignore_result=False)
def umount_task(driverCls, provider, identity, instance_id,
                volume_id, *args, **kwargs):
    try:
        celery_logger.debug("umount_task started at %s." % datetime.now())
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_id)
        volume = driver.get_volume(volume_id)
        attach_data = volume.extra['attachments'][0]
        device = attach_data['device']

        # Check mount to find the mount_location for device
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

        # Volume not mounted, move along..
        if not mount_location:
            return

        um_script = umount_volume(device)
        kwargs.update({'deploy': um_script})
        driver.deploy_to(instance, **kwargs)

        if 'is busy' in um_script.stdout:
            # Show all processes that are making device busy..
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
                    (search_dict['name'], search_dict['pid']))

            raise DeviceBusyException(mount_location, offending_processes)
        # Return here if no errors occurred..
        celery_logger.debug("umount_task finished at %s." % datetime.now())
    except DeviceBusyException:
        raise
    except Exception as exc:
        celery_logger.warn(exc)
        umount_task.retry(exc=exc)


@task(name="attach_task",
      default_retry_delay=20,
      ignore_result=False,
      max_retries=1)
def attach_task(driverCls, provider, identity, instance_id, volume_id,
                device_choice=None, *args, **kwargs):
    try:
        celery_logger.debug("attach_task started at %s." % datetime.now())
        driver = get_driver(driverCls, provider, identity)
        from service.volume import attach_volume  # TODO: Test pulling this up -- out of band
        attach_volume(driver, instance_id, volume_id, device_choice=device_choice)

        # When the reslt returns the volume will be 'attaching'
        # We can't do anything until the volume is 'available/in-use'
        attempts = 0
        while True:
            volume = driver.get_volume(volume_id)
            # Give up if you can't find the volume
            if not volume:
                return None
            if attempts > 6:  # After 6 attempts (~1min)
                break
            # Openstack Check
            if isinstance(driver, OSDriver) and\
                    'attaching' not in volume.extra.get('status', ''):
                break
            if isinstance(driver, EucaDriver) and\
                    'attaching' not in volume.extra.get('status', ''):
                break
            # Exponential backoff..
            attempts += 1
            sleep_time = 2**attempts
            celery_logger.debug("Volume %s is not ready (%s). Sleep for %s"
                         % (volume.id, volume.extra.get('status', 'no-status'),
                            sleep_time))
            time.sleep(sleep_time)

        if 'available' in volume.extra.get('status', ''):
            raise Exception("Volume %s failed to attach to instance %s"
                            % (volume.id, instance_id))

        # Device path for euca == openstack
        try:
            attach_data = volume.extra['attachments'][0]
            device = attach_data['device']
        except (IndexError, KeyError) as bad_fetch:
            celery_logger.warn("Could not find 'device' in "
                        "volume.extra['attachments']: "
                        "Volume:%s Extra:%s" % (volume.id, volume.extra))
            device = None

        celery_logger.debug("attach_task finished at %s." % datetime.now())
        return device
    except Exception as exc:
        celery_logger.exception(exc)
        attach_task.retry(exc=exc)


@task(name="detach_task",
      max_retries=1,
      default_retry_delay=20,
      ignore_result=False)
def detach_task(driverCls, provider, identity,
                instance_id, volume_id, *args, **kwargs):
    try:
        celery_logger.debug("detach_task started at %s." % datetime.now())
        driver = get_driver(driverCls, provider, identity)
        instance = driver.get_instance(instance_id)
        volume = driver.get_volume(volume_id)

        driver.detach_volume(volume)
        # When the reslt returns the volume will be 'detaching'
        # We will ensure the volume does not return to 'in-use'
        attempts = 0
        while True:
            volume = driver.get_volume(volume_id)
            if attempts > 6:  # After 6 attempts (~1min)
                break
            # The Openstack way
            if isinstance(driver, OSDriver)\
                    and 'detaching' not in volume.extra['status']:
                break
            # The Eucalyptus way
            attach_data = volume.extra['attachments'][0]
            if isinstance(driver, EucaDriver) and attach_data\
                    and 'detaching' not in attach_data.get('status'):
                break
            # Exponential backoff..
            attempts += 1
            sleep_time = 2**attempts
            celery_logger.debug("Volume %s is not ready (%s). Sleep for %s"
                         % (volume.id, volume.extra['status'], sleep_time))
            time.sleep(sleep_time)

        if 'in-use' in volume.extra['status']:
            raise Exception("Failed to detach Volume %s to instance %s"
                            % (volume, instance))

        celery_logger.debug("detach_task finished at %s." % datetime.now())
    except DeviceBusyException:
        # We should NOT retry if the device is busy
        raise
    except Exception as exc:
        # If the volume is NOT attached, do not retry.
        if 'Volume is not attached' in exc.message:
            return
        celery_logger.exception(exc)
        detach_task.retry(exc=exc)


@task(name="update_mount_location", max_retries=2, default_retry_delay=15)
def update_mount_location(new_mount_location,
                          driverCls, provider, identity,
                          volume_alias):
    """
    """
    from service import volume as volume_service
    try:
        celery_logger.debug(
            "update_mount_location task started at %s." %
            datetime.now())
        driver = get_driver(driverCls, provider, identity)
        volume = driver.get_volume(volume_alias)
        if not volume:
            return
        if not new_mount_location:
            return
        #volume_metadata = volume.extra['metadata']
        return volume_service._update_volume_metadata(
            driver, volume,
            metadata={'mount_location': new_mount_location})
        celery_logger.debug(
            "update_mount_location task finished at %s." %
            datetime.now())
    except Exception as exc:
        celery_logger.exception(exc)
        update_mount_location.retry(exc=exc)


@task(name="update_volume_metadata", max_retries=2, default_retry_delay=15)
def update_volume_metadata(driverCls, provider,
                           identity, volume_alias,
                           metadata):
    """
    """
    from service import volume as volume_service
    try:
        celery_logger.debug(
            "update_volume_metadata task started at %s." %
            datetime.now())
        driver = get_driver(driverCls, provider, identity)
        volume = driver.get_volume(volume_alias)
        if not volume:
            return
        return volume_service._update_volume_metadata(
            driver, volume,
            metadata=metadata)
        celery_logger.debug("volume_metadata task finished at %s." % datetime.now())
    except Exception as exc:
        celery_logger.exception(exc)
        update_volume_metadata.retry(exc=exc)

# Deploy and Destroy tasks


@task(name="mount_failed")
def mount_failed(
        context,
        exception_msg,
        traceback,
        driverCls, provider, identity, volume_id,
        unmount=False, **celery_task_args):
    from service import volume as volume_service
    try:
        celery_logger.debug("mount_failed task started at %s." % datetime.now())
        celery_logger.info("task context=%s" % context)
        err_str = "%s\nMount Error Traceback:%s" % (exception_msg, traceback)
        celery_logger.error(err_str)
        driver = get_driver(driverCls, provider, identity)
        volume = driver.get_volume(volume_id)
        if unmount:
            tmp_status = 'umount_error'
        else:
            tmp_status = 'mount_error'
        return volume_service._update_volume_metadata(
            driver, volume,
            metadata={'tmp_status': tmp_status})
        celery_logger.debug("mount_failed task finished at %s." % datetime.now())
    except Exception as exc:
        celery_logger.warn(exc)
        mount_failed.retry(exc=exc)
