from collections import namedtuple
from threepio import logger

from core.models.quota import get_quota, has_storage_count_quota,\
    has_storage_quota
from core.models.identity import Identity

from service.cache import get_cached_driver
from service.driver import _retrieve_source, prepare_driver

from service import exceptions
from service.instance import boot_volume_instance

# FIXME: fix prepare_driver to take a user directly
Request = namedtuple("request", ["user"])


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
    image_size = image._connection.get_size(image._image)
    if size > image_size + 4:
        raise exceptions.VolumeError(
            "Volumes created from images cannot exceed "
            "more than 4GB greater than the size of the image:%s GB"
            % size)


def create_volume_or_fail(name, size, user, provider, identity,
                          image_id=None, snapshot_id=None):
    snapshot = None
    image = None
    # FIXME: fix prepare_driver to take a user directly
    request = Request(user)
    driver = prepare_driver(request, provider.uuid, identity.uuid,
                            raise_exception=True)

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
    _, volume = create_volume(driver, identity.uuid, name, size,
                              snapshot=snapshot, image=image,
                              raise_exception=True)
    return volume


def create_volume(esh_driver, identity_uuid, name, size,
                  description=None, metadata=None, snapshot=None, image=None,
                  raise_exception=False):
    quota = get_quota(identity_uuid)
    if not has_storage_quota(esh_driver, quota, size):
        raise exceptions.OverQuotaError(
            message="Maximum total size of Storage Volumes Exceeded")
    if not has_storage_count_quota(esh_driver, quota, 1):
        raise exceptions.OverQuotaError(
            message="Maximum # of Storage Volumes Exceeded")
    # NOTE: Calling non-standard create_volume_obj so we know the ID
    # of newly created volume. Libcloud just returns 'True'... --Steve
    success, esh_volume = esh_driver.create_volume(
        size=size,
        name=name,
        metadata=metadata,
        snapshot=snapshot,
        image=image)

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
    provider = volume.instance_source.provider
    identity = volume.instance_source.created_by_identity
    # FIXME: fix prepare_driver to take a user directly
    request = Request(user)
    driver = prepare_driver(request, provider.uuid, identity.uuid,
                            raise_exception=True)

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
