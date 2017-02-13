import random
import time
from datetime import timedelta
from django.core.exceptions import ObjectDoesNotExist
import pytz
from django.db.models import Q
from django.utils import timezone
from threepio import logger
from core.models import AtmosphereUser as User
from core.models import AccountProvider
from core.models.allocation_strategy import Allocation as CoreAllocation
from core.models.allocation_strategy import AllocationStrategy as CoreAllocationStrategy
from core.models.credential import Credential
from core.models import IdentityMembership, Identity, InstanceStatusHistory
from core.models.instance import Instance as CoreInstance
from core.models.instance import (
    convert_esh_instance, _esh_instance_size_to_core
)
from core.models.size import convert_esh_size
from allocation.models import Allocation, AllocationResult
from service.cache import get_cached_instances, get_cached_driver
from service.instance import suspend_instance, stop_instance, destroy_instance, shelve_instance, offload_instance
from allocation.engine import calculate_allocation
from django.conf import settings
from rtwo.exceptions import LibcloudInvalidCredsError

# Private
def _include_all_idents(identities, owner_map):
    # Include all identities with 0 instances to the monitoring
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


def _core_instances_for(identity, start_date=None):
    if not start_date:
        # Can't use 'None' as a query value
        start_date = timezone.datetime(1970, 1, 1).replace(tzinfo=pytz.utc)
    return CoreInstance.objects.filter(
        Q(instancestatushistory__end_date=None) |
        Q(instancestatushistory__end_date__gt=start_date) |
        Q(end_date=None) | Q(end_date__gt=start_date),
        # NOTE: May need to remove this created_by line
        # down-the-road as we share user/tenants.
        created_by=identity.created_by,
        created_by_identity=identity).distinct()


def _select_identities(provider, users=None):
    if users:
        return provider.identity_set.filter(created_by__username__in=users)
    return provider.identity_set.all()


def _convert_tenant_id_to_names(instances, tenants):
    for i in instances:
        for tenant in tenants:
            if type(tenant) == dict:
                if tenant['id'] == i.owner:
                    i.owner = tenant['name']
            else:
                if tenant.id == i.owner:
                    i.owner = tenant.name
    return instances


def _get_identity_from_tenant_name(provider, username):
    try:
        # NOTE: I could see this being a problem when 'user1' and 'user2' use
        # TODO: Ideally we would be able to extract some more information
        #      when we move away from explicit user-groups.
        credential = Credential.objects.get(
            key='ex_project_name', value=username,
            identity__provider=provider,
            identity__created_by__username=username)
        identity = credential.identity
        return identity
    except Credential.MultipleObjectsReturned:
        logger.warn("%s has >1 Credentials on Provider %s"
                    % (username, provider))
        credential = Credential.objects.filter(
            key='ex_project_name', value=username,
            identity__provider=provider,
            identity__created_by__username=username)[0]
        identity = credential.identity
        return identity
    except Credential.DoesNotExist:
        return None

# Core Monitoring methods


def get_allocation_result_for(
        provider, username, print_logs=False, start_date=None, end_date=None):
    """
    Given provider and username:
    * Find the correct identity for the user
    * Create 'Allocation' using core representation
    * Calculate the 'AllocationResult' and return both
    """
    #FIXME: Remove this after debug testing is complete
    if print_logs:
        from service.tasks.monitoring import _init_stdout_logging, _exit_stdout_logging
        console_handler = _init_stdout_logging(logger)
    #ENDFIXME: Remove this after debug testing is complete

    identity = _get_identity_from_tenant_name(provider, username)
    # Attempt to run through the allocation engine
    try:
        allocation_result = _get_allocation_result(
            identity, start_date, end_date,
            print_logs=print_logs)
        if allocation_result.total_runtime() != timedelta(0):
            logger.debug("Result for Username %s: %s"
                         % (username, allocation_result))
        return allocation_result
    except IdentityMembership.DoesNotExist:
        logger.warn(
            "WARNING: User %s does not"
            "have IdentityMembership on this database" % (username, ))
        return _empty_allocation_result()
    except:
        logger.exception("Unable to monitor Identity:%s"
                         % (identity,))
        raise
    #FIXME: Remove this after debug testing is complete
    else:
        if print_logs:
            _exit_stdout_logging(console_handler)
    #ENDFIXME: Remove this after debug testing is complete


def user_over_allocation_enforcement(
        provider, username, print_logs=False, start_date=None, end_date=None):
    """
    Begin monitoring 'username' on 'provider'.
    * Calculate allocation from START of month to END of month
    * If user is deemed OverAllocation, apply enforce_allocation_policy
    """
    if settings.USE_ALLOCATION_SOURCE:
        logger.info("Settings dictate that USE_ALLOCATION_SOURCE = True."
                    " To manually enforce 'over-allocation', "
                    "call allocation_source_overage_enforcement(allocation_source)")
        return None
    identity = _get_identity_from_tenant_name(provider, username)
    allocation_result = get_allocation_result_for(
        provider, username,
        print_logs, start_date, end_date)
    # ASSERT: allocation_result has been retrieved successfully
    # Make some enforcement decision based on the allocation_result's output.

    if not identity:
        logger.warn(
            "%s has NO identity. "
            "Total Runtime could NOT be calculated. Returning.." %
            (username, ))
        return allocation_result
    user = User.objects.get(username=username)
    allocation = get_allocation(username, identity.uuid)
    if not allocation:
        logger.info(
            "%s has NO allocation. Total Runtime: %s. Returning.." %
            (username, allocation_result.total_runtime()))
        return allocation_result

    if not settings.ENFORCING:
        return allocation_result

    # Enforce allocation if overboard.
    over_allocation, diff_amount = allocation_result.total_difference()
    if over_allocation:
        logger.info(
            "%s is OVER allocation. %s - %s = %s"
            % (username,
               allocation_result.total_credit(),
               allocation_result.total_runtime(),
               diff_amount))
        try:
            enforce_allocation_policy(identity, user)
        except:
            logger.info("Unable to enforce allocation for user: %s" % user)
    return allocation_result


def enforce_allocation_policy(identity, user):
    """
    Add additional logic here to determine the proper 'action to take'
    when THIS identity/user combination is given
    #Possible combinations:
    1. Check the 'rules' for this provider
    2. Notify the 'ProviderAdministrator' that a user has exceeded
       their allocation, but that NO action has been taken.
    """
    return provider_over_allocation_enforcement(identity, user)


def _execute_provider_action(identity, user, instance, action_name):
    driver = get_cached_driver(identity=identity)
    logger.info("User %s has gone over their allocation on Instance %s - Enforcement Choice: %s" % (user, instance, action_name))
    try:
        if not action_name:
            logger.debug("No 'action_name' provided")
            return
        elif action_name == 'Suspend':
            suspend_instance(
                driver,
                instance,
                identity.provider.uuid,
                identity.uuid,
                user)
        elif action_name == 'Stop':
            stop_instance(
                driver,
                instance,
                identity.provider.uuid,
                identity.uuid,
                user)
        elif action_name == 'Shelve':
            shelve_instance(
                driver,
                instance,
                identity.provider.uuid,
                identity.uuid,
                user)
        elif action_name == 'Shelve Offload':
            offload_instance(
                driver,
                instance,
                identity.provider.uuid,
                identity.uuid,
                user)
        elif action_name == 'Terminate':
            destroy_instance(user, identity.uuid, instance)
        else:
            raise Exception("Encountered Unknown Action Named %s" % action)
    except ObjectDoesNotExist:
        # This may be unreachable when null,blank = True
        logger.debug(
            "Provider %s - 'Do Nothing' for Over Allocation" %
            provider)
        return


def provider_over_allocation_enforcement(identity, user):
    provider = identity.provider
    action = provider.over_allocation_action
    if not action:
        logger.debug("No 'over_allocation_action' provided for %s" % provider)
        return False
    if not settings.ENFORCING:
        logger.debug("Do not enforce over allocation action (%s) for provider %s, ENFORCING is disabled" % (action, provider))
        return False
    driver = get_cached_driver(identity=identity)
    esh_instances = driver.list_instances()
    # TODO: Parallelize this operation so you don't wait for larger instances
    # to finish 'wait_for' task below..
    for instance in esh_instances:
        execute_provider_action(user, driver, identity, instance, action)
    return True  # User was over_allocation


def update_instances(driver, identity, esh_list, core_list):
    """
    End-date core instances that don't show up in esh_list
    && Update the values of instances that do
    """
    esh_ids = [instance.id for instance in esh_list]
    # logger.info('%s Instances for Identity %s: %s'
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
        core_size = convert_esh_size(esh_size, identity.provider.uuid)
        core_instance.update_history(
            esh_instance.extra['status'],
            core_size,
            esh_instance.extra.get('task'),
            esh_instance.extra.get(
                'metadata', {}).get('tmp_status','MISSING'))

# Used in monitoring.py


def _cleanup_missing_instances(
        identity, core_running_instances, start_date=None):
    """
    Cleans up the DB InstanceStatusHistory when you know what instances are
    active...

    core_running_instances - Reference list of KNOWN active instances
    """
    instances = []

    if not identity:
        return instances

    core_instances = _core_instances_for(identity, start_date)
    fixed_instances = []
    for inst in core_instances:
        if not core_running_instances or inst not in core_running_instances:
            inst.end_date_all()
            fixed_instances.append(inst)
        else:
            # Instance IS in the list of running instances.. Further cleaning
            # can be done at this level.
            non_end_dated_history = inst.instancestatushistory_set.filter(
                end_date=None)
            count = len(non_end_dated_history)
            if count > 1:
                history_names = [ish.status.name for ish
                                 in non_end_dated_history]
                # Note: We have the 'wrong' instance, we want the one that
                # includes the ESH driver
                core_running_inst = [i for i in core_running_instances
                                     if i == inst][0]
                new_history = _resolve_history_conflict(
                    identity, core_running_inst, non_end_dated_history)
                fixed_instances.append(inst)
                logger.warn(
                    "Instance %s contained %s "
                    "NON END DATED history:%s. "
                    " New History: %s" %
                    (inst.provider_alias,
                     count, history_names, new_history))
            # Gather the updated values..
            instances.append(inst)
    # Return the updated list
    if fixed_instances:
        logger.warn("Cleaned up %s instances for %s"
                    % (len(fixed_instances), identity.created_by.username))
    return instances


def _resolve_history_conflict(
        identity, core_running_instance,
        bad_history, reset_time=None):
    """
    NOTE 1: This is a 'band-aid' fix until we are 100% that Transaction will
            not create conflicting un-end-dated objects.

    NOTE 2: It is EXPECTED that this instance has the 'esh' attribute
            Failure to add the 'esh' attribute will generate a ValueError!
    """
    if not getattr(core_running_instance, 'esh'):
        raise ValueError("Esh is missing from %s" % core_running_instance)
    esh_instance = core_running_instance.esh

    # Check for temporary status and fetch that
    tmp_status = esh_instance.extra.get('metadata', {}).get("tmp_status")
    new_status = tmp_status or esh_instance.extra['status']

    esh_driver = get_cached_driver(identity=identity)
    new_size = _esh_instance_size_to_core(
        esh_driver, esh_instance, identity.provider.uuid)
    if not reset_time:
        reset_time = timezone.now()
    for history in bad_history:
        history.end_date = reset_time
        history.save()
    new_history = InstanceStatusHistory.create_history(
        new_status,
        core_running_instance, new_size,
        reset_time)
    return new_history


def _get_instance_owner_map(provider, users=None):
    """
    All keys == All identities
    Values = List of identities / username
    NOTE: This is KEYSTONE && NOVA specific. the 'instance owner' here is the
          username // ex_tenant_name
    """
    from service.driver import get_account_driver

    admin_driver = get_cached_driver(provider=provider)
    accounts = get_account_driver(provider=provider)
    all_identities = _select_identities(provider, users)
    acct_providers = AccountProvider.objects.filter(provider=provider)
    if acct_providers:
        account_identity = acct_providers[0].identity
        provider = None
    else:
        account_identity = None


    all_instances = get_cached_instances(provider=provider, identity=account_identity, force=True)
    #all_tenants = admin_driver._connection._keystone_list_tenants()
    all_tenants = accounts.list_projects()
    # Convert instance.owner from tenant-id to tenant-name all at once
    all_instances = _convert_tenant_id_to_names(all_instances, all_tenants)
    # Make a mapping of owner-to-instance
    instance_map = _make_instance_owner_map(all_instances, users=users)
    logger.info("Instance owner map created")
    identity_map = _include_all_idents(all_identities, instance_map)
    logger.info("Identity map created")
    return identity_map
# Used in OLD allocation


def check_over_allocation(username, identity_uuid,
                          time_period=None):
    """
    Check if an identity is over allocation.

    NOTE: Answer is ALWAYS a 2-tuple
    True,False - Over/Under Allocation
    Amount - Time (amount) Over/Under Allocation.
    """
    identity = Identity.objects.get(uuid=identity_uuid)
    allocation_result = _get_allocation_result(identity)
    return allocation_result.total_difference()


def get_allocation(username, identity_uuid):
    user = User.objects.get(username=username)
    group = user.group_set.filter(name=user.username).first()
    if not group:
        logger.warn("WARNING: User %s does not have a group named %s" % (user, user.username))
        return None
    try:
        membership = IdentityMembership.objects.get(
            identity__uuid=identity_uuid, member=group)
    except IdentityMembership.DoesNotExist:
        logger.warn(
            "WARNING: User %s does not"
            "have IdentityMembership on this database" % (username, ))
        return None
    if not user.is_staff and not membership.allocation:
        def_allocation = CoreAllocation.default_allocation(
            membership.identity.provider)
        logger.warn("%s is MISSING an allocation. Default Allocation"
                    " assigned:%s" % (user, def_allocation))
        return def_allocation
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
        # Use allocation's delta value because no time period is set.
        return timedelta(minutes=allocation.delta)


def _empty_allocation_result():
    """
    """
    return AllocationResult.no_allocation()


def _get_allocation_result(identity, start_date=None, end_date=None,
                           print_logs=False, limit_instances=[], limit_history=[]):
    """
    Given an identity, retrieve the provider strategy and apply the strategy
    to this identity.
    """

    if not identity:
        return _empty_allocation_result()
    username = identity.created_by.username
    core_allocation = get_allocation(username, identity.uuid)
    if not core_allocation:
        logger.warn("User:%s Identity:%s does not have an allocation assigned"
                    % (username, identity))
    allocation_input = apply_strategy(
        identity, core_allocation,
        limit_instances=limit_instances, limit_history=limit_history,
        start_date=start_date, end_date=end_date)
    allocation_result = calculate_allocation(
        allocation_input,
        print_logs=print_logs)
    return allocation_result


def apply_strategy(identity, core_allocation, limit_instances=[], limit_history=[], start_date=None, end_date=None):
    """
    Given identity and core allocation, grab the ProviderStrategy
    and apply it. Returns an "AllocationInput"
    """
    strategy = _get_strategy(identity)
    if not strategy:
        return Allocation(credits=[], rules=[], instances=[],
            start_date=start_date, end_date=end_date)
    return strategy.apply(
        identity, core_allocation,
        limit_instances=limit_instances, limit_history=limit_history,
        start_date=start_date, end_date=end_date)


def _get_strategy(identity):
    try:
        return identity.provider.allocationstrategy
    except CoreAllocationStrategy.DoesNotExist:
        return None


def allocation_source_overage_enforcement(allocation_source):
    all_user_instances = {}
    for user in allocation_source.all_users:
        all_user_instances[user.username] = []
        for identity in user.current_identities:
            affected_instances = allocation_source_overage_enforcement_for(
                    allocation_source, user, identity)
            user_instances = all_user_instances[user.username]
            user_instances.extend(affected_instances)
            all_user_instances[user.username] = user_instances
    return all_user_instances


def filter_allocation_source_instances(allocation_source, esh_instances):
    #Circ Dep
    from core.models.allocation_strategy import InstanceAllocationSourceSnapshot
    as_instances = []
    for inst in esh_instances:
        provider_alias = inst.id
        snapshot = InstanceAllocationSourceSnapshot.objects.filter(
            instance__provider_alias=provider_alias).first()
        if snapshot and snapshot.allocation_source == allocation_source:
            as_instances.append(inst)
    return as_instances


def allocation_source_overage_enforcement_for(allocation_source, user, identity):
    provider = identity.provider
    action = provider.over_allocation_action
    if not action:
        logger.debug("No 'over_allocation_action' provided for %s" % provider)
        return []  # Over_allocation was not attempted
    if not settings.ENFORCING:
        logger.info("Settings dictate that ENFORCING = False. Returning..")
        return []
    try:
        driver = get_cached_driver(identity=identity)
        esh_instances = driver.list_instances()
    except LibcloudInvalidCredsError:
        raise Exception("User %s has invalid credentials on Identity %s" % (user, identity))
    filtered_instances = filter_allocation_source_instances(allocation_source, esh_instances)
    # TODO: Parallelize this operation so you don't wait for larger instances
    # to finish 'wait_for' task below..
    instances = []
    for instance in filtered_instances:
        core_instance = execute_provider_action(user, driver, identity, instance, action)
        instances.append(core_instance)
    return instances

def execute_provider_action(user, driver, identity, instance, action):
    try:
        if driver._is_active_instance(instance):
            # Suspend active instances, update the task in the DB
            # NOTE: identity.created_by COULD BE the Admin User, indicating that this action/InstanceHistory was
            #       executed by the administrator.. Future Release Idea.
            _execute_provider_action(
                identity,
                identity.created_by,
                instance,
                action.name)
            # NOTE: Intentionally added to allow time for
            #      the Cloud to begin 'suspend' operation
            #      before querying for the instance again.
            # TODO: Instead: Add "wait_for" change from active to any
            # terminal, non-active state?
            wait_time = random.uniform(2, 6)
            time.sleep(wait_time)
            updated_esh = driver.get_instance(instance.id)
            core_instance = convert_esh_instance(
                driver, updated_esh,
                identity.provider.uuid,
                identity.uuid,
                user)
            return core_instance
    except Exception as e:
        # Raise ANY exception that doesn't say
        # 'This instance is already in the requested VM state'
        # NOTE: This is OpenStack specific
        if 'in vm_state' not in e.message:
            raise
