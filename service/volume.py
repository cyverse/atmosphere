from threepio import logger

from django.core.exceptions import ValidationError
from core.models.quota import get_quota, has_storage_count_quota,\
    has_storage_quota
from core.models.identity import Identity
from core.models.volume import Volume
from core.models.instance_source import InstanceSource

from service.cache import get_cached_driver
from service.driver import _retrieve_source, get_esh_driver
from service.quota import check_over_storage_quota
from service import exceptions
from service.instance import boot_volume_instance


def update_volume_metadata(core_volume, metadata={}):
    identity = core_volume.source.created_by_identity
    volume_id = core_volume.provider_alias
    esh_driver = get_cached_driver(identity=identity)
    esh_volume = esh_driver.get_volume(volume_id)
    return _update_volume_metadata(esh_driver, esh_volume, metadata)


def _update_volume_metadata(esh_driver, esh_volume,
                            metadata={}):
    """
    NOTE: This will NOT WORK for TAGS until openstack
    allows JSONArrays as values for metadata!
    NOTE: This will NOT replace missing metadata tags..
    ex:
    Start: ('a':'value','c':'value')
    passed: c=5
    End: ('a':'value', 'c':5)
    """
    if not esh_volume:
        return {}

    if not hasattr(esh_driver._connection, 'ex_update_volume_metadata'):
        logger.warn(
            "EshDriver %s does not have function 'ex_update_volume_metadata'" %
            esh_driver._connection.__class__)
        return {}
    data = esh_volume.extra.get('metadata', {})
    data.update(metadata)
    try:
        return esh_driver._connection.ex_update_volume_metadata(
            esh_volume,
            data)
    except Exception as e:
        logger.exception("Error updating the metadata")
        if 'incapable of performing the request' in e.message:
            return {}
        else:
            raise


def restrict_size_by_image(size, image):
    image_bytes = image._image.extra.get('image_size', None)
    if not image_bytes:
        raise exceptions.VolumeError(
            "Cannot determine size of the image %s: "
            "Expected rtwo.models.machine.OSMachine to include "
            "'image_size' key in the 'extra' fields." % (image.name,))
    image_size = int(image_bytes / 1024.0**3)
    if size > image_size + 4:
        raise exceptions.VolumeError(
            "Volumes created from images cannot exceed "
            "more than 4GB greater than the size of the image:(%s GB)"
            % size)


def create_volume_or_fail(name, size, user, provider, identity,
                          description=None, project=None, image_id=None, snapshot_id=None):
    snapshot = None
    image = None
    driver = get_esh_driver(identity, username=user.username)

    if snapshot_id:
        snapshot = driver._connection.ex_get_snapshot(image_id)

    if image_id:
        image = driver.get_machine(image_id)
        restrict_size_by_image(size, image)

    #: Guard against both snapshot and image being present
    assert snapshot is None or image is None, (
        "A volume can only be constructed from a `snapshot` "
        "or an `image` not both.")

    #: Create the volume or raise an exception
    #NOTE: username can be removed when 'quota' is not linked to IdentityMembership
    _, esh_volume = create_esh_volume(driver, user.username, identity.uuid, name, size,
                              description=description,
                              snapshot=snapshot, image=image,
                              raise_exception=True)
    identifier = esh_volume.id
    start_date = esh_volume.extra.get('created_at')
    source = InstanceSource.objects.create(
        identifier=identifier,
        provider=provider,
        created_by=user,
        created_by_identity=identity)

    kwargs = {
        "name": name,
        "size": size,
        "description": description,
        "instance_source": source,
        "start_date": start_date
    }
    volume = Volume.objects.create(**kwargs)
    if project:
        project.volumes.add(volume)
    return volume


def create_snapshot(esh_driver, username, identity_uuid, name,
                    volume, description=None, raise_exception=False):
    if not volume:
        raise ValueError("Volume is required to create VolumeSnapshot")
    try:
        check_over_storage_quota(username, identity_uuid, new_snapshot_size=volume.size)
    except ValidationError as over_quota:
        raise exceptions.OverQuotaError(
            message=over_quota.message)
    esh_ss = esh_driver._connection.ex_create_snapshot(
        volume_id=volume.id,
        display_name=name,
        display_description=description)

    if not esh_ss and raise_exception:
        raise exceptions.VolumeError("The volume failed to be created.")

    return esh_ss


def create_esh_volume(esh_driver, username, identity_uuid, name, size,
                  description=None, metadata=None, snapshot=None, image=None,
                  raise_exception=False):
    quota = get_quota(identity_uuid)
    try:
        check_over_storage_quota(username, identity_uuid, new_volume_size=size)
    except ValidationError as over_quota:
        raise exceptions.OverQuotaError(
            message=over_quota.message)
    if not has_storage_count_quota(esh_driver, quota, 1):
        raise exceptions.OverQuotaError(
            message="Maximum # of Storage Volumes Exceeded")
    # NOTE: Calling non-standard create_volume_obj so we know the ID
    # of newly created volume. Libcloud just returns 'True'... --Steve
    conn_kwargs = {'max_attempts': 1}
    success, esh_volume = esh_driver.create_volume(
        size=size,
        name=name,
        metadata=metadata,
        snapshot=snapshot,
        image=image,
        **conn_kwargs)

    if not success and raise_exception:
        raise exceptions.VolumeError("The volume failed to be created.")

    return success, esh_volume


def destroy_volume_or_fail(volume, user, cascade=False):
    """
    Destroy the volume specified

    :param cascade: Cascades through and destroy volume snapshots
                    (defaults is False)
    :type cascade: ``bool``
    """
    identity = volume.instance_source.created_by_identity
    driver = get_esh_driver(identity, username=user.username)

    # retrieve volume or fail with not found
    esh_volume = driver.get_volume(volume.identifier)

    if esh_volume is None:
        raise exceptions.NotFound(
            "The `%s` could not be found."
            % volume.identifier)

    # if cascade True and snapshots exist delete all snapshots
    if cascade:
        snapshots = esh_volume.list_snapshots()
        for snapshot in snapshots:
            driver.destroy_snapshot(snapshot)

    # destroy the volume successfully or raise an exception
    if not driver.destroy_volume(esh_volume):
        raise Exception("Encountered an error destroying the volume.")


def create_bootable_volume(
        user,
        provider_uuid,
        identity_uuid,
        name,
        size_alias,
        new_source_alias,
        source_hint=None,
        **kwargs):
    """
    **kwargs passed as data to boot_volume_instance
    """

    identity = Identity.objects.get(uuid=identity_uuid)
    if not identity:
        raise Exception("Identity UUID %s does not exist." % identity_uuid)

    driver = get_cached_driver(identity=identity)
    if not driver:
        raise Exception(
            "Driver could not be initialized. Invalid Credentials?")

    size = driver.get_size(size_alias)
    if not size:
        raise Exception(
            "Size %s could not be located with this driver" % size_alias)

    # Return source or raises an Exception
    source = _retrieve_source(driver, new_source_alias, source_hint)

    core_instance = boot_volume_instance(driver, identity,
                                         source, size, name, **kwargs)

    return core_instance

def attach_volume(driver, instance_id, volume_id, device_choice=None):
    instance = driver.get_instance(instance_id)
    volume = driver.get_volume(volume_id)
    if volume.extra.get('status','N/A') in 'in-use':
        attachments = volume.extra['attachments']
        for attach_data in attachments:
            if instance_id in attach_data['serverId']:
                return volume
    # Step 1. Attach the volume
    # NOTE: device_choice !== device 100%
    return driver.attach_volume(instance,
                             volume,
                             device_choice)
