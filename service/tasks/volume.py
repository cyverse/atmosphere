"""
Tasks for volume operations.
"""
import re
import time

from django.utils import timezone

from celery import current_app as app
from celery.result import allow_join_result
from celery.decorators import task
from celery import chain

from threepio import celery_logger
from rtwo.driver import EucaDriver, OSDriver

from atmosphere.settings.local import ATMOSPHERE_PRIVATE_KEYFILE

from service.driver import get_driver
from service.deploy import (
    deploy_check_volume, deploy_mount_volume, deploy_unmount_volume,
    execution_has_failures, execution_has_unreachable)
from service.exceptions import DeviceBusyException

# Ansible deployment tasks

@task(name="check_volume_task",
      max_retries=0,
      default_retry_delay=20,
      ignore_result=False)
def check_volume_task(driverCls, provider, identity,
                      instance_id, volume_id, device_type='ext4', *args, **kwargs):
    try:
        celery_logger.debug("check_volume task started at %s." % timezone.now())
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
        playbook_results = deploy_check_volume(
            instance.ip, username, instance.id,
            device_location, device_type=device_type)
        success = not (execution_has_failures(playbook_results) or execution_has_unreachable(playbook_results))
        if not success:
            raise Exception(
                "Error encountered while checking volume for filesystem: instance_id: {}, volume_id: {}".format(instance_id, volume_id)
            )
        return success
    except Exception as exc:
        celery_logger.warn(exc)
        check_volume_task.retry(exc=exc)


@task(name="unmount_volume_task",
      max_retries=0,
      default_retry_delay=20,
      ignore_result=False)
def unmount_volume_task(driverCls, provider, identity, instance_id, volume_id,
               *args, **kwargs):
    try:
        celery_logger.debug("unmount task started at %s." % timezone.now())
        driver = get_driver(driverCls, provider, identity)
        username = identity.get_username()
        instance = driver.get_instance(instance_id)
        volume = driver.get_volume(volume_id)
        device_location = None

        try:
            attach_data = volume.extra['attachments'][0]
            device_location = attach_data['device']
        except (KeyError, IndexError):
            celery_logger.warn("Volume %s missing attachments in Extra"
                               % (volume,))
        if not device_location:
            raise Exception("No device_location found or inferred by volume %s" % volume)
        try:
            playbook_results = deploy_unmount_volume(
                instance.ip, username, instance.id, device_location)
        except DeviceBusyException:
            # Future-Fixme: Update VolumeStatusHistory.extra, set status to 'unmount_failed'
            raise
        if execution_has_failures(playbook_results) or execution_has_unreachable(playbook_results):
            raise Exception(
                "Error encountered while unmounting volume: instance_id: {}, volume_id: {}".format(instance_id, volume_id)
            )
        return device_location
    except Exception as exc:
        celery_logger.warn(exc)
        unmount_volume_task.retry(exc=exc)


@task(name="mount_volume_task",
      max_retries=0,
      default_retry_delay=20,
      ignore_result=False)
def mount_volume_task(driverCls, provider, identity, instance_id, volume_id,
               device_location, mount_location, device_type,
               mount_prefix=None, *args, **kwargs):
    try:
        celery_logger.debug("mount task started at %s." % timezone.now())
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

        playbook_results = deploy_mount_volume(
            instance.ip, username, instance.id,
            device_location, mount_location=mount_location, device_type=device_type)
        celery_logger.info(playbook_results)
        if execution_has_failures(playbook_results) or execution_has_unreachable(playbook_results):
            raise Exception(
                "Error encountered while mounting volume: instance_id: {}, volume_id: {}".format(instance_id, volume_id)
            )
        return mount_location
    except Exception as exc:
        celery_logger.warn(exc)
        mount_volume_task.retry(exc=exc)


# Libcloud Instance Action (Attachment) tasks


@task(name="attach_task")
def attach_task(driverCls,
                provider,
                identity,
                instance_id,
                volume_id,
                device_choice=None,
                *args,
                **kwargs):
    celery_logger.debug("attach_task started at %s." % timezone.now())
    driver = get_driver(driverCls, provider, identity)
    from service.volume import attach_volume
    attach_volume(driver, instance_id, volume_id, device_choice=device_choice)

    attempts = 0
    while True:
        volume = driver.get_volume(volume_id)
        assert volume, "Volume ({}) does not exist".format(volume_id)

        volume_status = volume.extra.get('status', '')
        if volume_status == "in-use":
            break

        if attempts > 4:
            raise Exception(
                "Attach task timed out for volume {} and instance {}, volume status: {}".
                format(volume_id, instance_id, volume_status))

        celery_logger.debug(
            "Volume {} is not ready. Expected 'in-use', got '{}'".format(
                volume_id, volume_status))
        time.sleep(10)
        attempts += 1

    try:
        attach_data = volume.extra['attachments'][0]
        device = attach_data['device']
    except (IndexError, KeyError):
        raise Exception("Could not find 'device' in volume.extra {}".format(
            volume.extra))

    celery_logger.debug("attach_task finished at %s." % timezone.now())
    return device


@task(name="detach_task",
      max_retries=1,
      default_retry_delay=20,
      ignore_result=False)
def detach_task(driverCls, provider, identity,
                instance_id, volume_id, *args, **kwargs):
    try:
        celery_logger.debug("detach_task started at %s." % timezone.now())
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

        celery_logger.debug("detach_task finished at %s." % timezone.now())
    except DeviceBusyException:
        # We should NOT retry if the device is busy
        raise
    except Exception as exc:
        # If the volume is NOT attached, do not retry.
        if 'Volume is not attached' in exc.message:
            return
        celery_logger.exception(exc)
        detach_task.retry(exc=exc)

# Volume metadata tasks


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
            timezone.now())
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
            timezone.now())
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
            timezone.now())
        driver = get_driver(driverCls, provider, identity)
        volume = driver.get_volume(volume_alias)
        if not volume:
            return
        return volume_service._update_volume_metadata(
            driver, volume,
            metadata=metadata)
        celery_logger.debug("volume_metadata task finished at %s." % timezone.now())
    except Exception as exc:
        celery_logger.exception(exc)
        update_volume_metadata.retry(exc=exc)

# Exception handling tasks


@task(name="mount_failed")
def mount_failed(
        context,
        exception_msg,
        traceback,
        driverCls, provider, identity, volume_id,
        unmount=False, **celery_task_args):
    from service import volume as volume_service
    try:
        celery_logger.debug("mount_failed task started at %s." % timezone.now())
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
        celery_logger.debug("mount_failed task finished at %s." % timezone.now())
    except Exception as exc:
        celery_logger.warn(exc)
        mount_failed.retry(exc=exc)


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
