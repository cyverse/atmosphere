from service.allocation import check_allocation

from api import get_esh_driver
from core.models import IdentityMembership, Identity

from threepio import logger

def get_current_quota(identity_id):
    driver = get_esh_driver(Identity.objects.get(id=identity_id))
    cpu = ram = disk = 0
    for instance in driver.list_instances():
        size = instance.size
        cpu += size.cpu
        ram += size.ram
        disk += size._size.disk
    return {'cpu':cpu, 'ram':ram, 'disk':disk}

def check_quota(username, identity_id, esh_size):
    membership = IdentityMembership.objects.get(identity__id=identity_id,
                                                member__name=username)
    quota_limit = membership.quota
    current = get_current_quota(identity_id)
    cur_cpu, cur_ram, cur_disk = current['cpu'], current['ram'], current['disk']
    new_cpu, new_ram, new_disk = esh_size.cpu, esh_size.ram, esh_size._size.disk
    if cur_cpu + new_cpu > quota_limit.cpu:
        logger.debug("Current:%s + New: %s > Quota: %s"\
                    % (cur_cpu, new_cpu, quota_limit.cpu))
        return False
    if cur_ram + new_ram > quota_limit.memory * 1024:  # Quota memory GB -> MB
        logger.debug("Current:%s + New: %s > Quota: %s"\
                    % (cur_ram, new_ram, quota_limit.memory*1024))
        return False
    if not check_allocation(username, identity_id):
        return False
    return True
