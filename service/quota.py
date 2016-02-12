from threepio import logger

from core.models import IdentityMembership, Identity, Provider

from service.accounts.openstack_manager import AccountDriver
from service.cache import get_cached_driver


def _get_hard_limits(provider):
    """
    At some point this will be a DIRECT relationship to the provider. But for
    now its hard-coded
    """
    return {"ram": 500, "cpu": 64}


def set_provider_quota(identity_uuid, limit_dict=None):
    """
    """
    identity = Identity.objects.get(uuid=identity_uuid)
    if not identity.credential_set.all():
        # Can't update quota if credentials arent set
        return
    if not limit_dict:
        limit_dict = _get_hard_limits(identity.provider)
    if identity.provider.get_type_name().lower() == 'openstack':
        driver = get_cached_driver(identity=identity)
        username = identity.created_by.username
        user_id = driver._connection._get_user_id()
        tenant_id = driver._connection._get_tenant_id()
        membership = IdentityMembership.objects.get(
            identity__uuid=identity_uuid,
            member__name=username)
        user_quota = membership.quota
        if user_quota:
            # Don't go above the hard-set limits per provider.
            if user_quota.cpu > limit_dict['cpu']:
                user_quota.cpu = limit_dict['cpu']
            if user_quota.memory > limit_dict['ram']:
                user_quota.memory = limit_dict['ram']
            # Use THESE values...
            values = {'cores': user_quota.cpu,
                      'ram': user_quota.memory * 1024}
            logger.info("Updating quota for %s to %s" % (username, values))
            ad = AccountDriver(identity.provider)
            admin_driver = ad.admin_driver
            admin_driver._connection.ex_update_quota_for_user(tenant_id,
                                                              user_id,
                                                              values)
    return True


def get_current_quota(identity_uuid):
    driver = get_cached_driver(
        identity=Identity.objects.get(uuid=identity_uuid))
    cpu = ram = disk = suspended = 0
    instances = driver.list_instances()
    # prefetch sizes
    sizes = {size.id:size for size in driver.list_sizes()}
    for instance in instances:
        if instance.extra['status'] == 'suspended'\
                or instance.extra['status'] == 'shutoff':
            suspended += 1
            continue
        size = sizes[instance.size.id]
        cpu += size.cpu
        ram += size.ram
        disk += size.disk
    return {'cpu': cpu, 'ram': ram, 'disk': disk, 'suspended_count': suspended}


def check_over_quota(username, identity_uuid, esh_size=None, resuming=False):
    """
    Checks quota based on current limits (and an instance of size, if passed).

    return 5-tuple: ((bool) over_quota,
                     (str) resource_over_quota,
                     (int) number_requested,
                     (int) number_used,
                     (int) number_allowed)
    """
    membership = IdentityMembership.objects.get(identity__uuid=identity_uuid,
                                                member__name=username)
    user_quota = membership.quota

    current = get_current_quota(identity_uuid)
    logger.debug("Current Quota:%s" % current)
    cur_cpu = current['cpu']
    cur_ram = current['ram']
    cur_disk = current['disk']
    cur_suspended = current['suspended_count']

    # Add new size to current, check user quota
    new_cpu = cur_cpu
    new_ram = cur_ram
    new_disk = cur_disk
    if esh_size:
        new_cpu += esh_size.cpu
        new_ram += esh_size.ram
        new_disk += esh_size.disk
        logger.debug("Quota including size: %s"
                     % ({'cpu': cur_cpu, 'ram': cur_ram,
                         'disk': cur_disk}))
    if resuming:
        logger.debug("User is resuming an already suspended instance")
        new_suspended = cur_suspended
    else:
        new_suspended = cur_suspended + 1
        logger.debug("User attempting to suspend/launch another instance")

    # Quota tests here
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
