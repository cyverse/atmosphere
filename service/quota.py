from threepio import logger

from core.models import IdentityMembership, Identity
from core.models.quota import (
    has_floating_ip_count_quota,
    has_port_count_quota,
    has_instance_count_quota,
    has_cpu_quota,
    has_mem_quota,
    has_suspended_count_quota,
    has_storage_quota,
    has_storage_count_quota,
    has_snapshot_count_quota
    )
from service.cache import get_cached_driver
from service.driver import get_account_driver


def check_over_instance_quota(
        username, identity_uuid,
        esh_size=None, action=None):
    """
    Checks quota based on current limits (and an instance of size, if passed).

    return or raise exc
    """
    membership = IdentityMembership.objects.get(
        identity__uuid=identity_uuid,
        member__name=username)
    quota = membership.quota
    identity = membership.identity
    driver = get_cached_driver(identity=identity)
    new_port = new_floating_ip = new_instance = new_cpu = new_ram = 0
    if esh_size:
        new_cpu += esh_size.cpu
        new_ram += esh_size.ram
    if action in ['launch', 'resume', 'reboot', 'unshelve']:
        new_floating_ip += 1
        new_instance += 1
        new_port += 1
    # Will throw ValidationError if false.
    has_cpu_quota(driver, quota, new_cpu)
    has_mem_quota(driver, quota, new_ram)
    has_instance_count_quota(driver, quota, new_instance)
    has_suspended_count_quota(driver, quota)
    has_floating_ip_count_quota(driver, quota, new_floating_ip)
    has_port_count_quota(driver, quota, new_port)
    return True


def check_over_storage_quota(
        username, identity_uuid,
        new_snapshot_size=0, new_volume_size=0):
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
    quota = membership.quota
    identity = membership.identity
    driver = get_cached_driver(identity=identity)
    new_disk = new_volume_size or new_snapshot_size
    new_volume = 1 if new_volume_size > 0 else 0
    new_snapshot = 1 if new_snapshot_size > 0 else 0
    # Will throw ValidationError if false.
    has_storage_quota(driver, quota, new_disk)
    has_storage_count_quota(driver, quota, new_volume)
    has_snapshot_count_quota(driver, quota, new_snapshot)
    return True


def set_provider_quota(identity_uuid, limit_dict=None):
    """
    """
    identity = Identity.objects.get(uuid=identity_uuid)
    if not identity.credential_set.all():
        # Can't update quota if credentials arent set
        return
    username = identity.created_by.username
    membership = IdentityMembership.objects.get(
        identity__uuid=identity_uuid,
        member__name=username)
    user_quota = membership.quota

    if not user_quota:
        # Can't update quota if it doesn't exist
        return True
    # Don't go above the hard-set limits per provider.
    _limit_user_quota(user_quota, identity, limit_dict=limit_dict)

    return _set_openstack_quota(user_quota, identity)


def _get_hard_limits(identity):
    """
    Lookup the OpenStack "Hard Limits" based on the account provider
    """
    accounts = get_account_driver(identity.provider)
    defaults = {"ram": 999, "cpu": 99}  # Used when all else fails.
    limits = {}
    limits.update(defaults)
    username = identity.get_credential('key')
    project_name = identity.get_credential('ex_project_name')
    user_limits = accounts.get_quota_limit(username, project_name)
    if user_limits:
        limits.update(user_limits)
    return limits


def _set_openstack_quota(
        user_quota, identity, compute=True, volume=True, network=True):
    if not identity.provider.get_type_name().lower() == 'openstack':
        raise Exception("Cannot set provider quota on type: %s"
                        % identity.provider.get_type_name())

    if compute:
        compute_quota = _set_compute_quota(user_quota, identity)
    if network:
        network_quota = _set_network_quota(user_quota, identity)
    if volume:
        volume_quota = _set_volume_quota(user_quota, identity)

    return {
        'compute': compute_quota,
        'network': network_quota,
        'volume': volume_quota,
    }


def _limit_user_quota(user_quota, identity, limit_dict=None):
    if not limit_dict:
        limit_dict = _get_hard_limits(identity)
    if user_quota.cpu > limit_dict['cpu']:
        user_quota.cpu = limit_dict['cpu']
    if user_quota.memory > limit_dict['ram']:
        user_quota.memory = limit_dict['ram']
    return user_quota


def _set_network_quota(user_quota, identity):
    network_values = {
        'port': user_quota.port_count,
        'floatingip': user_quota.floating_ip_count,
        # INTENTIONALLY SKIPPED/IGNORED
        # 'subnet', 'router', 'network',
        # 'security_group', 'security_group_rules'
    }
    username = identity.created_by.username
    logger.info("Updating network quota for %s to %s"
                % (username, network_values))
    driver = get_cached_driver(identity=identity)
    tenant_id = driver._connection._get_tenant_id()

    ad = get_account_driver(identity.provider)
    admin_driver = ad.admin_driver
    admin_driver._connection._neutron_update_quota(tenant_id, network_values)
    return


def _set_volume_quota(user_quota, identity):
    volume_values = {
        'volumes': user_quota.storage_count,
        'gigabytes': user_quota.memory,
        'snapshots': user_quota.snapshot_count,
    }
    username = identity.created_by.username
    logger.info("Updating quota for %s to %s" % (username, volume_values))
    driver = get_cached_driver(identity=identity)
    username = driver._connection._get_username()
    ad = get_account_driver(identity.provider)
    admin_driver = ad.admin_driver
    admin_driver._connection._cinder_update_quota(username, volume_values)
    return


def _set_compute_quota(user_quota, identity):
    # Use THESE values...
    compute_values = {
        'cores': user_quota.cpu,
        'ram': user_quota.memory,  # NOTE: Test that this works on havana
        'floating_ips': user_quota.floating_ip_count,
        'fixed_ips': user_quota.port_count,
        'instances': user_quota.instance_count,
    }
    username = identity.created_by.username
    logger.info("Updating quota for %s to %s" % (username, compute_values))
    driver = get_cached_driver(identity=identity)
    user_id = driver._connection.key
    tenant_id = driver._connection._get_tenant_id()
    ad = get_account_driver(identity.provider)
    admin_driver = ad.admin_driver
    return admin_driver._connection.ex_update_quota_for_user(
        tenant_id, user_id, compute_values)
