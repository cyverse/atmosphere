from api import get_esh_driver
from core.models import IdentityMembership, Identity
from service.allocation import check_allocation

from threepio import logger

def get_current_quota(identity_id):
    driver = get_esh_driver(Identity.objects.get(id=identity_id))
    cpu = ram = disk = suspended = 0
    instances = driver.list_instances()
    for instance in instances:
        if instance.extra['status'] == 'suspended':
            suspended += 1
            continue
        size = instance.size
        cpu += size.cpu
        ram += size.ram
        disk += size._size.disk
    return {'cpu':cpu, 'ram':ram, 'disk':disk, 'suspended_count':suspended}

def check_over_quota(username, identity_id, esh_size=None):
    """
    Checks quota based on current limits (and an instance of size, if passed).
    return False if quota is OK
    return True if quota is exceeded
    """
    membership = IdentityMembership.objects.get(identity__id=identity_id,
                                                member__name=username)
    user_quota = membership.quota

    current = get_current_quota(identity_id)
    logger.debug("Current Quota:%s" % current)
    cur_cpu = current['cpu']
    cur_ram = current['ram']
    cur_disk = current['disk']
    cur_suspended = current['suspended_count']

    # Add new size to current, check user quota
    if esh_size:
        cur_cpu += esh_size.cpu
        cur_ram += esh_size.ram
        cur_disk += esh_size._size.disk
        cur_suspended += 1
        logger.debug("Quota including size: %s"\
                     % ({'cpu':cur_cpu, 'ram':cur_ram,
                     'disk':cur_disk, 'suspended_count':cur_suspended}))

    #Quota tests here
    if cur_cpu > user_quota.cpu:
        logger.debug("quota exceeded on cpu: %s" 
                    % user_quota.cpu)
        return True
    elif cur_ram > user_quota.memory * 1024:  # Quota memory GB -> MB
        logger.debug("quota exceeded on memory: %s GB" 
                    % user_quota.cpu)
        return True
    elif cur_suspended > user_quota.suspended_count:
        logger.debug("Quota exceed on suspended instances: %s"
                     % user_quota.suspended_count)
        return True
    return False
