import sys

from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from threepio import logger

from core.models import AtmosphereUser as User
from core.models import IdentityMembership, Identity
from core.models.instance import Instance, convert_esh_instance

from service.cache import get_cached_instances, get_cached_driver
from allocation.models import AllocationIncrease,\
        AllocationRecharge, AllocationUnlimited,\
        IgnoreStatusRule, MultiplySizeCPU,\
        Allocation, TimeUnit
from allocation.models import Instance as AllocInstance




##Print functions from OLD allocation
def print_table_header():
    print "Username,Allocation allowed (min),Allocation Used (min),"\
          "Instance,Status,Size (name),Size (CPUs),Start_Time,"\
          "End_Time,Active_Time,Cpu_Time"

def print_instances(instance_status_map, user, allocation, time_used):
    max_time_allowed = timedelta(minutes=allocation.threshold)
    print "Username:%s Time allowed: %s Time Used: %s"\
          % (user.username,
             strfdelta(max_time_allowed),
             strfdelta(time_used))
    print 'Instances that counted against %s:' % (user.username,)
    for instance, status_list in instance_status_map.items():
        for history in status_list:
            if history.cpu_time > timedelta(0):
                print "Instance %s, Size %s (%s CPU), Start:%s, End:%s,"\
                      " Active time:%s CPU time:%s" %\
                  (instance.provider_alias,
                   history.size.name, history.size.cpu,
                   strfdate(history.start_count), strfdate(history.end_count),
                   strfdelta(history.active_time), strfdelta(history.cpu_time))

def print_table_row(instance_status_map, user, allocation, time_used):
    max_time_allowed = timedelta(minutes=allocation.threshold)
    print "%s,%s,%s,,,,,,,,,,"\
          % (user.username,
             strfdelta(max_time_allowed),
             strfdelta(time_used))
    for instance, status_list in instance_status_map.items():
        for history in status_list:
            print ",,,%s,%s,%s,%s,%s,%s,%s,%s" %\
                  (instance.provider_alias,
                   history.status.name,
                   history.size.name, history.size.cpu,
                   strfdate(history.start_count), strfdate(history.end_count),
                   strfdelta(history.active_time), strfdelta(history.cpu_time))

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
def get_instance_owner_map(provider, users=None):
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
def check_over_allocation(username, identity_id,
                          time_period=None):
    """
    Check if an identity is over allocation.

    If time_period is timedelta(month=1) then delta_time is from the
    beginning of the month to now otherwise delta_time is allocation.delta.
    Get all instance histories created between now and delta_time. Check
    that cumulative time of instances do not exceed threshold.

    True if allocation has been exceeded, otherwise False.
    """
    allocation = get_allocation(username, identity_id)
    if not allocation:
        return (False, timedelta(0))
    delta_time = get_delta(allocation, time_period)
    max_time_allowed = timedelta(minutes=allocation.threshold)
    logger.debug("%s Allocation: %s Time allowed"
                 % (username, max_time_allowed))
    total_time_used, _ = core_instance_time(username, identity_id, delta_time)
    logger.debug("%s Time Used: %s"
                 % (username, total_time_used))
    time_diff = max_time_allowed - total_time_used
    if time_diff.total_seconds() <= 0:
        logger.debug("%s is OVER their allowed quota by %s" %
                     (username, time_diff))
        return (True, time_diff)
    return (False, time_diff)


def get_allocation(username, identity_id):
    membership = IdentityMembership.objects.get(identity__id=identity_id,
                                                member__name=username)
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


def get_burn_time(user, identity_id, delta, threshold, now_time=None):
    """
    INPUT: Total time allowed, total time used (so far),
    OUTPUT: delta representing time remaining (from now)
    """
    #DONT MOVE -- Circ.Dep.
    from service.instance import get_core_instances
    #Allow for multiple 'types' to be sent in
    if type(user) is not User:
        #not user, so this is a str with username
        user = User.objects.filter(username=user)
    if type(delta) is not timedelta:
        #not delta, so this is the int for minutes
        delta = timedelta(minutes=delta)
    if type(threshold) is not timedelta:
        #not delta, so this is the int for minutes
        delta = timedelta(minutes=threshold)

    #Assume we are burned out.
    burn_time = timedelta(0)

    #If we have no instances, burn-time does not apply
    instances = get_core_instances(identity_id)
    if not instances:
        return burn_time

    #Remaining time: What your allotted - What you used before now
    time_used, _ = core_instance_time(
            user, identity_id, delta,
            now_time=now_time)
    #delta = delta - delta
    time_remaining = threshold - time_used

    #If we used all of our allocation, we are burned out.
    if time_remaining < timedelta(0):
        return burn_time

    cpu_cores = get_cpu_count(user, identity_id)
    #If we have no active cores, burn-time does not apply
    if cpu_cores == 0:
        return burn_time
    #Calculate burn time by dividing remaining time over running cores
    #delta / int = delta (ex. 300 mins / 3 = 100 mins)
    burn_time = time_remaining/cpu_cores
    return burn_time


def get_cpu_count(user, identity_id):
    #Counting only running instances:
    instances = Instance.objects.filter(
            end_date=None, created_by=user,
            created_by_identity__id=identity_id)
    #Looking at only the last history
    cpu_total = 0
    for inst in instances:
        last_history = inst.get_last_history()
        if last_history and last_history.is_active():
            cpu_total += last_history.size.cpu
    return cpu_total


def current_instance_time(user, instances, identity_id, delta_time,
                            end_date=None):
    """
    Converts all running instances to core, 
    so that the database is up to date before calling 'core_instance_time'
    """
    ident = Identity.objects.get(id=identity_id)
    driver = get_cached_driver(identity=ident)
    core_instance_list = [
        convert_esh_instance(driver, inst,
                             ident.provider.id, ident.id, user)
        for inst in instances]
    #All instances that don't have an end-date should be
    #included, even if all of their time is not.
    time_used = core_instance_time(user, ident.id, delta_time,
            running=core_instance_list, now_time=end_date)
    return time_used


def core_instance_time(user, identity_id, delta, running=[], now_time=None):
    """
    Called 'core_instance' time because it relies on the data
    in core to be relevant. 
    
    If you (potentially) have new instances on the
    driver, you should be using current_instance_time
    """
    if type(user) is not User:
        user = User.objects.filter(username=user)[0]
    if type(delta) is not timedelta:
        delta = timedelta(minutes=delta)

    total_time = timedelta(0)
    if not now_time:
        now_time = timezone.now() 
    past_time = now_time - delta
    #DevNote: If delta represents 'settings.FIXED_WINDOW' this value is
    #         the first of the month, UTC.

    #Calculate only the specific users time allocation.. UP to the now_time.
    instances = Instance.objects.filter(
            Q(end_date=None) | Q(end_date__gt=past_time),
            created_by=user, created_by_identity__id=identity_id)
    instance_status_map = {}
    for idx, i in enumerate(instances):
        #If we know what instances are running, and this isn't one of them,
        # it missed end-dating. Lets do something about it
        if running and i not in running:
            i.end_date_all()
        active_time, status_list = i.get_active_time(past_time, now_time)
        instance_status_map[i] = status_list
        new_total = active_time + total_time
        total_time = new_total
    return total_time, instance_status_map

def delta_to_minutes(tdelta):
    total_seconds = tdelta.days*86400 + tdelta.seconds
    total_mins = total_seconds / 60
    return total_mins


def delta_to_hours(tdelta):
    total_mins = delta_to_minutes(tdelta)
    hours = total_mins / 60
    return hours
