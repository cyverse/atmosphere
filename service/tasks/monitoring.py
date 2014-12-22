import time
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from django.conf import settings

from celery.decorators import task

from core.models.group import Group, IdentityMembership
from core.models.size import convert_esh_size
from core.models.instance import convert_esh_instance, Instance
from core.models.user import AtmosphereUser
from core.models.provider import Provider
from core.models.credential import Credential

from service.monitoring import get_delta, get_allocation,\
    _get_instance_owner_map, _cleanup_instances,\
    _create_allocation_input, _get_allocation_result
from service.cache import get_cached_driver, get_cached_instances

from threepio import logger


def strfdelta(tdelta, fmt=None):
    from string import Formatter
    if not fmt:
        #The standard, most human readable format.
        fmt = "{D} days {H:02} hours {M:02} minutes {S:02} seconds"
    if tdelta == timedelta():
        return "0 minutes"
    formatter = Formatter()
    return_map = {}
    div_by_map = {'D': 86400, 'H': 3600, 'M': 60, 'S': 1}
    keys = map(lambda x: x[1], list(formatter.parse(fmt)))
    remainder = int(tdelta.total_seconds())

    for unit in ('D', 'H', 'M', 'S'):
        if unit in keys and unit in div_by_map.keys():
            return_map[unit], remainder = divmod(remainder, div_by_map[unit])

    return formatter.format(fmt, **return_map)


def strfdate(datetime_o, fmt=None):
    if not fmt:
        #The standard, most human readable format.
        fmt = "%m/%d/%Y %H:%M:%S"
    if not datetime_o:
        datetime_o = timezone.now()

    return datetime_o.strftime(fmt)


@task(name="monitor_instances")
def monitor_instances():
    """
    Update instances for each active provider.
    """
    for p in Provider.get_active():
        monitor_instances_for.apply_async(args=[p.id])


@task(name="monitor_instances_for", queue="celery_periodic")
def monitor_instances_for(provider_id, users=None,
                          print_logs=False, start_date=None, end_date=None):
    """
    Update instances for provider.
    """
    provider = Provider.objects.get(id=provider_id)

    #For now, lets just ignore everything that isn't openstack.
    if 'openstack' not in provider.type.name.lower():
        return

    instance_map = _get_instance_owner_map(provider, users=users)

    if print_logs:
        import logging
        import sys
        consolehandler = logging.StreamHandler(sys.stdout)
        consolehandler.setLevel(logging.DEBUG)
        logger.addHandler(consolehandler)

    for username in sorted(instance_map.keys()):
        instances = instance_map[username]
        monitor_instances_for_user(provider, username, instances,
                                    print_logs, start_date, end_date)
    if print_logs:
        logger.removeHandler(consolehandler)

def monitor_instances_for_user(provider, username, instances,
                               print_logs=False, start_date=None, end_date=None):
    """
    Begin monitoring 'username' on 'provider'.
    All active 'esh' instances are passed in.
    * Calculate allocation from START of month to END of month
    * Create a "TEST" For enforce_allocation
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
    driver = get_cached_driver(identity=identity)
    esh_instances = driver.list_instances()
    for instance in esh_instances:
        try:
            if driver._is_active_instance(instance):
                #Suspend active instances, update the task in the DB
                driver.suspend_instance(instance)
                #Give it a few seconds to suspend
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

