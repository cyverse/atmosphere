from core.models.quota import get_quota, has_storage_count_quota,\
        has_storage_quota
from threepio import logger
from service.instance import network_init
from service.exceptions import OverQuotaError
from core.models.identity import Identity

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
        logger.warn("EshDriver %s does not have function 'ex_update_volume_metadata'"
                    % esh_driver._connection.__class__)
        return {}
    data = esh_volume.extra.get('metadata',{})
    data.update(metadata)
    try:
        return esh_driver._connection.ex_update_volume_metadata(esh_volume, data)
    except Exception, e:
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
    #NOTE: Calling non-standard create_volume_obj so we know the ID
    # of newly created volume. Libcloud just returns 'True'... --Steve
    success, esh_volume = esh_driver.create_volume(
        size=size,
        name=name,
        metadata=metadata,
        snapshot=snapshot,
        image=image)
    return success, esh_volume

def boot_volume(esh_driver, identity_uuid, name, size, source_obj=None, source_type=None, **kwargs):
    """
    If not image and volume: boot the volume, it already has na image on it
    If image and not volume: boot a new volume with a copy of image on it
    If image and volume: raise
    """
    #TODO: Prepare a network for the user
    core_identity = Identity.objects.get(uuid=identity_uuid)
    network = network_init(core_identity)
    success, server_obj = esh_driver._connection.ex_boot_volume(
            source_obj, source_type, name, size, network,
            **kwargs)
    if server_obj.has_key('server'):
        instance_id = server_obj["server"]["id"]
        instance = esh_driver.get_instance(instance_id)
        return instance
    else:
        logger.info(server_obj)
        return server_obj
