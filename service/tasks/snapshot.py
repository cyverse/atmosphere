"""
Manage snapshots for volumes and images
"""
from celery.decorators import task
from celery.exceptions import SoftTimeLimitExceeded

from threepio import logger

from core.models import Identity
from core.models.volume import convert_esh_volume

from service.cache import get_cached_driver


@task(name="create_volume_snapshot",
      default_retry_delay=15,
      soft_time_limit=15,
      max_retries=3,
      ignore_results=True)
def create_volume_snapshot(identity_uuid, volume_id, name, description):
    """
    Create a new volume snapshot
    """
    try:
        identity = Identity.objects.get(uuid=identity_uuid)
        driver = get_cached_driver(identity=identity)

        esh_volume = driver._connection.ex_get_volume(volume_id)

        if not esh_volume:
            raise Exception("No volume found for id=%s." % volume_id)

        snapshot = driver._connection.ex_create_snapshot(
            esh_volume, name, description)

        if not snapshot:
            raise Exception("The snapshot could not be created.")
    except SoftTimeLimitExceeded as e:
        logger.info("Task too long to complete. Task will be retried")
        create_volume_snapshot.retry(exc=e)
    except Identity.DoesNotExist:
        logger.info("An Identity for uuid=%s does not exist.", identity_uuid)
        raise


@task(name="delete_volume_snapshot",
      default_retry_delay=15,
      soft_time_limit=15,
      max_retries=3,
      ignore_results=True)
def delete_volume_snapshot(identity_uuid, snapshot_id):
    """
    Delete an existing volume snapshot
    """
    try:
        identity = Identity.objects.get(uuid=identity_uuid)
        driver = get_cached_driver(identity=identity)
        snapshot = driver._connection.ex_get_snapshot(snapshot_id)

        if not snapshot:
            raise Exception("No snapshot found for id=%s." % snapshot_id)

        success = driver._connection.ex_delete_snapshot(snapshot)

        if not success:
            raise Exception("Unable to delete snapshot with id=%s" %
                            snapshot_id)
    except SoftTimeLimitExceeded as e:
        delete_volume_snapshot.retry(exc=e)
    except Identity.DoesNotExist:
        logger.info("An Identity for uuid=%s does not exist.", identity_uuid)
        raise


@task(name="create_volume_from_image",
      default_retry_delay=15,
      soft_time_limit=15,
      max_retries=3,
      ignore_results=True)
def create_volume_from_image(identity_uuid, image_id, size_id, name,
                             description, metadata):
    """
    Create a new volume from an image
    """
    try:
        identity = Identity.objects.get(uuid=identity_uuid)
        user = identity.created_by
        driver = get_cached_driver(identity=identity)
        image = driver._connection.ex_get_image(image_id)
        size = driver._connection.ex_get_size(size_id)

        if not image:
            raise Exception("No image found for id=%s." % image_id)

        if not size:
            raise Exception("No size found for id=%s." % size_id)

        success, esh_volume = driver._connection.create_volume(
            size.id, name, description=description, metadata=metadata,
            image=image)

        if not success:
            raise Exception("Could not create volume from image")

        # Save the new volume to the database
        convert_esh_volume(
            esh_volume, identity.provider.uuid, identity_uuid, user)
    except SoftTimeLimitExceeded as e:
        create_volume_from_image.retry(exc=e)
    except Identity.DoesNotExist:
        logger.info("An Identity for uuid=%s does not exist.", identity_uuid)
        raise


@task(name="create_volume_from_snapshot",
      default_retry_delay=15,
      soft_time_limit=15,
      max_retries=3,
      ignore_results=True)
def create_volume_from_snapshot(identity_uuid, snapshot_id, size_id, name,
                                description, metadata):
    """
    Create a new volume for the snapshot

    NOTE: The size must be at least the same size as the original volume.
    """
    try:
        identity = Identity.objects.get(uuid=identity_uuid)
        driver = get_cached_driver(identity=identity)
        snapshot = driver._connection.ex_get_snapshot(snapshot_id)
        size = driver._connection.ex_get_size(size_id)

        if not snapshot:
            raise Exception("No snapshot found for id=%s." % snapshot_id)

        if not size:
            raise Exception("No size found for id=%s." % size_id)

        success, esh_volume = driver._connection.create_volume(
            snapshot.size, name, description=description, metadata=metadata,
            snapshot=snapshot)

        if not success:
            raise Exception("Could not create volume from snapshot")

        # Save the new volume to the database
        convert_esh_volume(
            esh_volume, identity.provider.uuid, identity_uuid,
            identity.created_by)
    except SoftTimeLimitExceeded as e:
        create_volume_from_snapshot.retry(exc=e)
    except Identity.DoesNotExist:
        logger.info("An Identity for uuid=%s does not exist.", identity_uuid)
        raise
