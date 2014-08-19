from core.models.quota import get_quota, has_storage_count_quota,\
        has_storage_quota
from service.instance import network_init
from service.exceptions import OverQuotaError
from core.models.identity import Identity


def create_volume(esh_driver, identity_id, name, size, description=None,
        metadata=None, snapshot=None, image=None):
    identity = Identity.objects.get(id=identity_id)
    quota = get_quota(identity_id)
    if not has_storage_quota(esh_driver, quota, size):
        raise OverQuotaError(
                message="Maximum total size of Storage Volumes Exceeded")
    if not has_storage_count_quota(esh_driver, quota, 1):
        raise OverQuotaError(
                message="Maximum # of Storage Volumes Exceeded")
    success, esh_volume = esh_driver.create_volume(
        size=size,
        name=name,
        description=description,
        metadata=metadata,
        snapshot=snapshot,
        image=image)
    return success, esh_volume

def boot_volume(esh_driver, identity_id, name, size, source_obj=None, source_type=None, **kwargs):
    """
    If not image and volume: boot the volume, it already has na image on it
    If image and not volume: boot a new volume with a copy of image on it
    If image and volume: raise
    """
    #TODO: Prepare a network for the user
    core_identity = Identity.objects.get(id=identity_id)
    network = network_init(core_identity)
    response, r_object = esh_driver._connection.ex_boot_volume(
            source_obj, source_type, name, size, network,
            **kwargs)
    return response, r_object


