from threepio import logger

from api import get_esh_driver

from core.models import IdentityMembership, Identity, Provider


def set_provider_quota(identity_id):
    """
    
    """
    identity = Identity.objects.get(id=identity_id)
    if not identity.credential_set.all():
        #Can't update quota if credentials arent set
        return
    if identity.provider.get_type_name().lower() == 'openstack':
        driver = get_esh_driver(identity)
        user_id = driver._connection.connection.auth_user_info['id']
        tenant_id = driver._connection._get_tenant_id()
        admin_driver = driver.meta().admin_driver
        membership = IdentityMembership.objects.get(identity__id=identity_id,
                                                    member__name=username)
        user_quota = membership.quota
        if user_quota:
            values = {'cores': user_quota.cpu,
                      'ram': user_quota.memory * 1024}
            admin_driver._connection.ex_update_quota_for_user(tenant_id,
                                                              user_id,
                                                              values)
    return True


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


def check_over_quota(username, identity_id, esh_size=None, resuming=False):
    """
    Checks quota based on current limits (and an instance of size, if passed).

    return 5-tuple: ((bool) over_quota,
                     (str) resource_over_quota,
                     (int) number_requested,
                     (int) number_used,
                     (int) number_allowed)
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
        new_cpu = cur_cpu + esh_size.cpu
        new_ram = cur_ram + esh_size.ram
        new_disk = cur_disk + esh_size._size.disk
        logger.debug("Quota including size: %s"\
                     % ({'cpu':cur_cpu, 'ram':cur_ram,
                     'disk':cur_disk}))
    if resuming:
        logger.debug("User is resuming an already suspended instance")
        new_suspended = cur_suspended
    else:
        new_suspended = cur_suspended + 1
        logger.debug("User attempting to suspend/launch another instance")

    #Quota tests here
    if new_cpu > user_quota.cpu:
        logger.debug("quota exceeded on cpu: %s" 
                    % user_quota.cpu)
        return (True, 'cpu', esh_size.cpu, cur_cpu, user_quota.cpu)
    elif new_ram > user_quota.memory * 1024:  # Quota memory GB -> MB
        logger.debug("quota exceeded on memory: %s GB" 
                    % user_quota.cpu)
        return (True, 'ram', esh_size.ram, cur_ram, user_quota.memory)
    elif not resuming and new_suspended > user_quota.suspended_count:
        logger.debug("Quota exceed on suspended instances: %s"
                     % user_quota.suspended_count)
        return (True, 'suspended instance', 1,
                cur_suspended, user_quota.suspended_count)
    return (False, '', 0, 0, 0)

