import sys

from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from threepio import logger

from core.models import AtmosphereUser as User
from core.models import IdentityMembership, Identity
from core.models.instance import Instance, convert_esh_instance

from service.cache import get_cached_instances, get_cached_driver
from allocation.engine import calculate_allocation
from allocation.models import AllocationIncrease,\
        AllocationRecharge, AllocationUnlimited,\
        IgnoreStatusRule, MultiplySizeCPU,\
        Allocation, TimeUnit
from allocation.models import Instance as AllocInstance
from django.conf import settings


## Deps Used in monitoring.py
def _include_all_idents(identities, owner_map):
    #Include all identities with 0 instances to the monitoring
    identity_owners = [ident.get_credential('ex_tenant_name')
                       for ident in identities]
    owners_w_instances = owner_map.keys()
    for user in identity_owners:
        if user not in owners_w_instances:
            owner_map[user] = []
    return owner_map
def _make_instance_owner_map(instances, users=None):
    owner_map = {}

    for i in instances:
        if users and i.owner not in users:
            continue
        key = i.owner
        instance_list = owner_map.get(key, [])
        instance_list.append(i)
        owner_map[key] = instance_list
    return owner_map

def _select_identities(provider, users=None):
    if users:
        return provider.identity_set.filter(created_by__username__in=users)
    return provider.identity_set.all()


def _convert_tenant_id_to_names(instances, tenants):
    for i in instances:
        for tenant in tenants:
            if tenant['id'] == i.owner:
                i.owner = tenant['name']
    return instances

## Used in monitoring.py
def _create_allocation_input(username, core_allocation, instances, window_start, window_stop, delta=None):
    """
    This function is meant to create an allocation input that
    is identical in functionality to that of the ORIGINAL allocation system.
    """
    if core_allocation:
        initial_recharge = AllocationRecharge(
                name="%s Assigned allocation" % username,
                unit=TimeUnit.minute, amount=core_allocation.threshold,
                recharge_date=window_start)
    else:
        initial_recharge = AllocationUnlimited(window_start)
    #Noteably MISSING: 'active', 'running'
    multiply_by_cpu = MultiplySizeCPU(name="Multiply TimeUsed by CPU", multiplier=1)
    ignore_inactive = IgnoreStatusRule("Ignore Inactive StatusHistory", value=["build", "pending",
        "hard_reboot", "reboot",
         "migrating", "rescue",
         "resize", "verify_resize",
        "shutoff", "shutting-down",
        "suspended", "terminated",
        "deleted", "error", "unknown","N/A",
        ])
    alloc_instances = [AllocInstance.from_core(inst, window_start) for inst in instances]
    return Allocation(
            credits=[initial_recharge],
            rules=[multiply_by_cpu, ignore_inactive], instances=alloc_instances,
            start_date=window_start, end_date=window_stop,
            interval_delta=delta)

    
def _cleanup_instances(core_instances, core_running_instances):
    """
    Cleans up the DB InstanceStatusHistory when you know what instances are
    active...

    core_instances - List of 'ALL' core instances
    core_running_instances - Reference list of KNOWN active instances
    """
    instances = []
    for inst in core_instances:
        if not core_running_instances or inst not in core_running_instances:
            inst.end_date_all()
        #Gather the updated values..
        instances.append(inst)
    #Return the updated list
    return instances
def _get_instance_owner_map(provider, users=None):
    """
    All keys == All identities
    Values = List of identities / username
    NOTE: This is KEYSTONE && NOVA specific. the 'instance owner' here is the
          username // ex_tenant_name
    """
    admin_driver = get_cached_driver(provider=provider)
    all_identities = _select_identities(provider, users)
    all_instances = get_cached_instances(provider=provider)
    all_tenants = admin_driver._connection._keystone_list_tenants()
    #Convert instance.owner from tenant-id to tenant-name all at once
    all_instances = _convert_tenant_id_to_names(all_instances, all_tenants)
    #Make a mapping of owner-to-instance
    instance_map = _make_instance_owner_map(all_instances, users=users)
    logger.info("Instance owner map created")
    identity_map = _include_all_idents(all_identities, instance_map)
    logger.info("Identity map created")
    return identity_map



## Used in OLD allocation
def check_over_allocation(username, identity_uuid,
                          time_period=None):
    """
    Check if an identity is over allocation.

    True if allocation has been exceeded, otherwise False.
    """
    identity = Identity.objects.get(uuid=identity_uuid)
    allocation_result = _get_allocation_result(identity)
    return (allocation_result.over_allocation(), 
            allocation_result.total_difference())


def get_allocation(username, identity_uuid):
    user = User.objects.get(username=username)
    membership = IdentityMembership.objects.get(identity__uuid=identity_uuid,
                                                member__user=user)
    if not user.is_staff and not membership.allocation:
        default_allocation = Allocation.default_allocation(
                membership.identity.provider)
        logger.warn("%s is MISSING an allocation. Default Allocation"
                    " assigned:%s" % (user,default_allocation))
        return default_allocation
    return membership.allocation


def get_delta(allocation, time_period, end_date=None):
    # Monthly Time Allocation
    if time_period and time_period.months == 1:
        now = end_date if end_date else timezone.now()
        if time_period.day <= now.day:
            allocation_time = timezone.datetime(year=now.year,
                                                month=now.month,
                                                day=time_period.day,
                                                tzinfo=timezone.utc)
        else:
            prev = now - time_period
            allocation_time = timezone.datetime(year=prev.year,
                                                month=prev.month,
                                                day=time_period.day,
                                                tzinfo=timezone.utc)
        return now - allocation_time
    else:
        #Use allocation's delta value because no time period is set.
        return timedelta(minutes=allocation.delta)


def _get_allocation_result(identity, start_date=None, end_date=None,
                           running_instances=[], print_logs=False):
    """
    Given an identity (And, optionally, time frame + list of running instances)
    Create an allocation input, run it against the engine and return the result
    """
    user = identity.created_by
    allocation = get_allocation(user.username, identity.uuid)
    if not allocation:
        logger.warn("User:%s Identity:%s does not have an allocation" % (user.username, identity))
    if not end_date:
        end_date = timezone.now()
    if not start_date:
        delta_time = get_delta(allocation, settings.FIXED_WINDOW, end_date)
        start_date = end_date - delta_time
    else:
        delta_time = end_date - start_date
    #Guaranteed a range (IF BOTH are NONE: Starting @ FIXED_WINDOW until NOW)
    #Convert running to esh..
    if running_instances:
        driver = get_cached_driver(identity=identity)
        core_running_instances = [
            convert_esh_instance(driver, inst,
                identity.provider.id, identity.id,
                identity.created_by.username) for inst in running_instances]

    #Retrieve the 'remaining' core that could have an impact..
    core_instances = Instance.objects.filter(
                    Q(end_date=None) | Q(end_date__gt=start_date),
                            created_by=identity.created_by,
                            created_by_identity__uuid=identity.uuid)

    if running_instances:
        #Since we know which instances are still active and which are not
        #Why not end_date ones that 'think' they are still running?
        #TODO: When this is a seperate maintenance task, we should seperate concerns.
        core_instances = _cleanup_instances(core_instances, core_running_instances)

    #Wow, so easy, I'm sure nothing is behind this curtain...
    allocation_input = _create_allocation_input(
            user.username, allocation, core_instances, start_date, end_date, delta_time)
    allocation_result = calculate_allocation(allocation_input,
            print_logs=print_logs)
    return allocation_result

