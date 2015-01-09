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


## Private
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
## Core Monitoring methods
def get_allocation_result_for(provider, username, instances,
                               print_logs=False, start_date=None, end_date=None):
    """
    Given provider, username and instances:
    * Find the correct identity for the user
    * Convert all 'Esh' instances to core representation
    * Create 'Allocation' using core representation
    * Calculate the 'AllocationResult' and return both
    """
    try:
        #NOTE: I could see this being a problem when 'user1' and 'user2' use
        #      ex_project_name == 'shared_group'
        #TODO: Ideally we would be able to extract some more information
        #      when we move away from explicit user-groups.
        credential = Credential.objects.get(
                key='ex_project_name', value=username,
                identity__provider=provider,
                identity__created_by__username=username)
        identity = credential.identity
    except Credential.DoesNotExist, no_creds:
        if instances:
            logger.warn("WARNING: ex_tenant_name: %s has %s instances, but does not"
                        "exist on this database." % (username, len(instances)))
        return
    #Attempt to run through the allocation engine
    try:
        allocation_result = _get_allocation_result(
                identity, start_date, end_date, running_instances=instances,
                print_logs=print_logs)
        logger.debug("Result for Username %s: %s"
                % (username, allocation_result))
    except IdentityMembership.DoesNotExist:
        if instances:
            logger.warn(
                "WARNING: User %s has %s instances, but does not"
                "have IdentityMembership on this database" % (username, len(instances)))
    except:
        logger.exception("Unable to monitor Identity:%s"
                         % (identity,))
        raise
    return allocation_result

def monitor_instances_for_user(provider, username, instances,
                               print_logs=False, start_date=None, end_date=None):
    """
    Begin monitoring 'username' on 'provider'.
    All active 'esh' instances are passed in.
    * Calculate allocation from START of month to END of month
    * Create a "TEST" For enforce_allocation
    """
    #ASSERT: allocation_result has been retrieved successfully
    #Make some enforcement decision based on the allocation_result's output.
    if not allocation:
        logger.info(
                "%s has NO allocation. Total Runtime: %s. Returning.." %
                (username, allocation_result.total_runtime()))
        return allocation_result

    if not settings.ENFORCING:
        logger.debug('Settings dictate allocations are NOT enforced')
        return allocation_result

    #Enforce allocation if overboard.
    if allocation_result.over_allocation():
        logger.info("%s is OVER allocation. %s - %s = %s"
                % (username, 
                    allocation_result.total_credit(),
                    allocation_result.total_runtime(),
                    allocation_result.total_difference()))
        enforce_allocation(identity, user)
    return allocation_result



def enforce_allocation(identity, user):
    """
    Add additional logic here to determine the proper 'action to take'
    when THIS identity/user combination is given
    """
    return suspend_all_instances_for(identity, user)

def suspend_all_instances_for(identity, user):
    driver = get_cached_driver(identity=identity)
    esh_instances = driver.list_instances()
    for instance in esh_instances:
        try:
            if driver._is_active_instance(instance):
                #Suspend active instances, update the task in the DB
                driver.suspend_instance(instance)
                #NOTE: Intentionally added to allow time for 
                #      the Cloud to begin 'suspend' operation 
                #      before querying for the instance again.
                time.sleep(3)
                updated_esh = driver.get_instance(instance.id)
                updated_core = convert_esh_instance(
                    driver, updated_esh,
                    identity.provider.id,
                    identity.id,
                    user)
        except Exception, e:
            #Raise ANY exception that doesn't say
            #'This instance is already suspended'
            if 'in vm_state suspended' not in e.message:
                raise
    return True  # User was over_allocation


def update_instances(driver, identity, esh_list, core_list):
    """
    End-date core instances that don't show up in esh_list
    && Update the values of instances that do
    """
    esh_ids = [instance.id for instance in esh_list]
    #logger.info('%s Instances for Identity %s: %s'
    #            % (len(esh_ids), identity, esh_ids))
    for core_instance in core_list:
        try:
            index = esh_ids.index(core_instance.provider_alias)
        except ValueError:
            logger.info("Did not find instance %s in ID List: %s" %
                        (core_instance.provider_alias, esh_ids))
            core_instance.end_date_all()
            continue
        esh_instance = esh_list[index]
        esh_size = driver.get_size(esh_instance.size.id)
        core_size = convert_esh_size(esh_size, identity.provider.id)
        core_instance.update_history(
            esh_instance.extra['status'],
            core_size,
            esh_instance.extra.get('task') or
            esh_instance.extra.get(
                'metadata', {}).get('tmp_status'))

## Used in monitoring.py

def _create_monthly_window_input(identity, core_allocation, running_instances,
        start_date, end_date, interval_delta=None):
    """
    This function is meant to create an allocation input that
    is identical in functionality to that of the ORIGINAL allocation system.
    """

    if not end_date:
        end_date = timezone.now()

    if not start_date:
        delta_time = get_delta(core_allocation, settings.FIXED_WINDOW, end_date)
        start_date = end_date - delta_time
    else:
        delta_time = end_date - start_date
    #TODO: I wanted delta_time.. why?
    #Guaranteed a range (IF BOTH are NONE: Starting @ FIXED_WINDOW until NOW)
    if core_allocation:
        initial_recharge = AllocationRecharge(
                name="%s Assigned allocation" % identity.created_by.username,
                unit=TimeUnit.minute, amount=core_allocation.threshold,
                recharge_date=start_date)
    else:
        initial_recharge = AllocationUnlimited(start_date)
    if running_instances:
        #Convert running to esh..
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

    #TODO: We should seperate concerns. This should be a seperate maintenance
    #      task..
    if running_instances:
        #Since we know which instances are still active and which are not
        #Why not end_date ones that 'think' they are still running?
        core_instances = _cleanup_instances(core_instances, core_running_instances)

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
    #Convert Core Models --> Allocation/core Models
    alloc_instances = [AllocInstance.from_core(inst, start_date)
                       for inst in core_instances]
    return Allocation(
            credits=[initial_recharge],
            rules=[multiply_by_cpu, ignore_inactive], instances=alloc_instances,
            start_date=start_date, end_date=end_date,
            interval_delta=interval_delta)

    
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
    Given an identity (And, optionally, time frame + list of instances):
    * Provide defaults that are similar to the 'monthly window' conditions in
    Previous Versions
    * Create an allocation input, run it against the engine and return the result
    """
    username = identity.created_by.username
    core_allocation = get_allocation(username, identity.uuid)
    if not core_allocation:
        logger.warn("User:%s Identity:%s does not have an allocation assigned"
                % (username, identity))
    #TODO: Logic should be placed HERE when we decide to move away from
    #      'fixed monthly window' calculations.
    allocation_input = _create_monthly_window_input(identity, core_allocation,
            running_instances, start_date, end_date)

    allocation_result = calculate_allocation(allocation_input, print_logs=print_logs)
    return allocation_result

