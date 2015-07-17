from djcelery.app import app
from django.conf import settings

from threepio import logger

from core.models.quota import get_quota, has_storage_count_quota,\
    has_storage_quota
from core.models.identity import Identity

from service.cache import get_cached_driver
from service.driver import _retrieve_source

from service.instance import boot_volume_instance
from service.exceptions import OverQuotaError


def update_volume_metadata(esh_driver, esh_volume,
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
    wait_time = 1
    if not esh_volume:
        return {}
    volume_id = esh_volume.id

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


def create_volume(esh_driver, identity_uuid, name, size,
                  description=None, metadata=None, snapshot=None, image=None):
    identity = Identity.objects.get(uuid=identity_uuid)
    quota = get_quota(identity_uuid)
    if not has_storage_quota(esh_driver, quota, size):
        raise OverQuotaError(
            message="Maximum total size of Storage Volumes Exceeded")
    if not has_storage_count_quota(esh_driver, quota, 1):
        raise OverQuotaError(
            message="Maximum # of Storage Volumes Exceeded")
    # NOTE: Calling non-standard create_volume_obj so we know the ID
    # of newly created volume. Libcloud just returns 'True'... --Steve
    success, esh_volume = esh_driver.create_volume(
        size=size,
        name=name,
        metadata=metadata,
        snapshot=snapshot,
        image=image)
    return success, esh_volume


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

    identity = CoreIdentity.objects.get(uuid=identity_uuid)
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

    core_instance = boot_volume_instance(esh_driver, identity,
                                         source, size, name, **data)

    return core_instance
