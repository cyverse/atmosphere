from core.models.quota import get_quota, has_storage_count_quota,\
        has_storage_quota
from service.exceptions import OverQuotaError
from core.models.identity import Identity


def create_volume(esh_driver, identity_id, name, size, description=None):
    identity = Identity.objects.get(id=identity_id)
    quota = get_quota(identity_id)
    if not has_storage_quota(esh_driver, quota, size):
        raise OverQuotaError(
                "Maximum total size of Storage Volumes Exceeded")
    if not has_storage_count_quota(esh_driver, quota, 1):
        raise OverQuotaError(
                "Maximum # of Storage Volumes Exceeded")
    success, esh_volume = esh_driver.create_volume(
        name=name,
        size=size,
        description=description)
    return success, esh_volume
