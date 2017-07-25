from threepio import logger

from django.core.exceptions import ValidationError

from core.models import IdentityMembership, Identity
from core.models.quota import (
    has_floating_ip_count_quota,
    has_port_count_quota,
    has_instance_count_quota,
    has_cpu_quota,
    has_mem_quota,
    has_storage_quota,
    has_storage_count_quota,
    has_snapshot_count_quota
    )
from service.cache import get_cached_driver
from service.driver import get_account_driver


def check_over_instance_quota(
        username, identity_uuid, esh_size=None,
        include_networking=False, raise_exc=True):
    """
    Checks quota based on current limits (and an instance of size, if passed).
    param - esh_size - if included, update the CPU and Memory totals & increase instance_count
    param - launch_networking - if True, increase floating_ip_count
    param - raise_exc - if True, raise ValidationError, otherwise return False

    return True if passing
    return False if ValidationError occurs and raise_exc=False
    By default, allow ValidationError to raise.

    return or raise exc
    """
    memberships_available = IdentityMembership.objects.filter(
        identity__uuid=identity_uuid,
        member__memberships__user__username=username)
    if memberships_available:
        membership = memberships_available.first()
    identity = membership.identity
    quota = identity.quota
    driver = get_cached_driver(identity=identity)
    new_port = new_floating_ip = new_instance = new_cpu = new_ram = 0
    if esh_size:
        new_cpu += esh_size.cpu
        new_ram += esh_size.ram
        new_instance += 1
        new_port += 1
    if include_networking:
        new_floating_ip += 1
    # Will throw ValidationError if false.
    try:
        has_cpu_quota(driver, quota, new_cpu)
        has_mem_quota(driver, quota, new_ram)
        has_instance_count_quota(driver, quota, new_instance)
        has_floating_ip_count_quota(driver, quota, new_floating_ip)
        has_port_count_quota(identity, driver, quota, new_port)
        return True
    except ValidationError:
        if raise_exc:
            raise
        return False


def check_over_storage_quota(
        username, identity_uuid,
        new_snapshot_size=0, new_volume_size=0, raise_exc=True):
    """
    Checks quota based on current limits.
    param - new_snapshot_size - if included and non-zero, increase snapshot_count
    param - new_volume_size - if included and non-zero, add to storage total & increase storage_count
    param - raise_exc - if True, raise ValidationError, otherwise return False

    return True if passing
    return False if ValidationError occurs and raise_exc=False
    By default, allow ValidationError to raise.
    """
    memberships_available = IdentityMembership.objects.filter(
        identity__uuid=identity_uuid,
        member__memberships__user__username=username)
    if memberships_available:
        membership = memberships_available.first()
    identity = membership.identity
    quota = identity.quota
    driver = get_cached_driver(identity=identity)

    # FIXME: I don't believe that 'snapshot' size and 'volume' size share
    # the same quota, so for now we ignore 'snapshot-size',
    # and only care that value is 0 or >1
    new_snapshot = 1 if new_snapshot_size > 0 else 0

    new_disk = new_volume_size
    new_volume = 1 if new_volume_size > 0 else 0
    # Will throw ValidationError if false.
    try:
        has_storage_quota(driver, quota, new_disk)
        has_storage_count_quota(driver, quota, new_volume)
        has_snapshot_count_quota(driver, quota, new_snapshot)
        return True
    except ValidationError:
        if raise_exc:
            raise
        return False


def set_provider_quota(identity_uuid, quota=None, limit_dict=None):
    """
    """
    identity = Identity.objects.get(uuid=identity_uuid)
    if not quota:
        quota = identity.quota
    if not identity.credential_set.all():
        # NOTE: This special-case is here to prevent 'new identities'
        # that have not included a set of credentials from
        # causing task failures
        return
    provider = identity.provider
    if provider.get_type_name() == 'mock':
        return

    # NOTE: You can use the 'limit_dict' to avoid
    # going above the hard-set limits per provider.
    # see _get_hard_limits or pass in {'ram': ### (GB), 'cpu': ### (Cores)}
    # _limit_user_quota(user_quota, identity, limit_dict=limit_dict)

    return set_openstack_quota(identity, user_quota=quota)


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


def set_openstack_quota(
        identity, user_quota=None, compute=True, volume=True, network=True):
    if not identity.provider.get_type_name().lower() == 'openstack':
        raise Exception("Cannot set provider quota on type: %s"
                        % identity.provider.get_type_name())
    if not user_quota:
        user_quota = identity.quota
    if not user_quota:
        # Can't update quota if it doesn't exist
        raise Exception("No quota set for identity - %s" % identity)

    if compute:
        compute_quota = _set_compute_quota(user_quota, identity)
    if network:
        network_quota = _set_network_quota(user_quota, identity)
    if volume:
        volume_quota = _set_volume_quota(user_quota, identity)

    return {
        'account': {
            'identity': identity.project_name(),
            'quota': str(user_quota),
        },
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
    result = admin_driver._connection._neutron_update_quota(tenant_id, network_values)
    logger.info("Updated quota for %s to %s" % (username, result))
    return result


def _set_volume_quota(user_quota, identity):
    volume_values = {
        'volumes': user_quota.storage_count,
        'gigabytes': user_quota.storage,
        'snapshots': user_quota.snapshot_count,
    }
    username = identity.created_by.username
    logger.info("Updating quota for %s to %s" % (username, volume_values))
    driver = get_cached_driver(identity=identity)
    username = driver._connection._get_username()
    ad = get_account_driver(identity.provider)
    admin_driver = ad.admin_driver
    result = admin_driver._connection._cinder_update_quota(username, volume_values)
    logger.info("Updated quota for %s to %s" % (username, result))
    return result


def _set_compute_quota(user_quota, identity):
    # Use THESE values...
    compute_values = {
        'cores': user_quota.cpu,
        'ram': user_quota.memory*1024,  # NOTE: Value is stored in GB, Openstack (Liberty) expects MB
        'floating_ips': user_quota.floating_ip_count,
        'fixed_ips': user_quota.port_count,
        'instances': user_quota.instance_count,
    }
    creds = identity.get_all_credentials()
    use_tenant_id = False
    if creds.get('ex_force_auth_version', '2.0_password') == "2.0_password":
        compute_values.pop('instances')
        use_tenant_id = True

    username = identity.created_by.username
    logger.info("Updating quota for %s to %s" % (username, compute_values))
    driver = get_cached_driver(identity=identity)
    username = driver._connection.key
    tenant_id = driver._connection._get_tenant_id()
    ad = get_account_driver(identity.provider, raise_exception=True)
    ks_user = ad.get_user(username)
    admin_driver = ad.admin_driver
    creds = identity.get_all_credentials()
    if creds.get('ex_force_auth_version', '2.0_password') != "2.0_password":
        # FIXME: Remove 'use_tenant_id' when legacy clouds are no-longer in use.
        try:
            result = admin_driver._connection.ex_update_quota(tenant_id, compute_values, use_tenant_id=use_tenant_id)
        except Exception:
            logger.exception("Could not set a user-quota, trying to set tenant-quota")
            raise
        # FIXME: For jetstream, return result here.
    # For CyVerse old clouds, run the top method. don't use try/except.
    try:
        result = admin_driver._connection.ex_update_quota_for_user(
            tenant_id, ks_user.id, compute_values, use_tenant_id=use_tenant_id)
    except Exception:
        logger.exception("Could not set a user-quota, trying to set tenant-quota")
        raise
    logger.info("Updated quota for %s to %s" % (username, result))
    return result
