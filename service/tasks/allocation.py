import time

from api import get_esh_driver
from datetime import timedelta

from django.utils import timezone
from django.conf import settings

from celery.decorators import task

from core.models.group import Group
from core.models.size import convert_esh_size
from core.models.user import AtmosphereUser
from core.models.provider import Provider

from service.allocation import current_instance_time,\
    get_delta, get_allocation
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


def get_instance_owner_map(provider, users=None):
    """
    All keys == All identities
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


@task(name="monitor_instances_for", queue="celery_periodic")
def monitor_instances_for(provider_id, users=None,
                          print_logs=False, end_date=None):
    """
    Update instances for provider.
    """
    #For now, lets just ignore everything that isn't openstack.
    provider = Provider.objects.get(id=provider_id)
    if 'openstack' not in provider.type.name.lower():
        return

    instance_map = get_instance_owner_map(provider, users=users)

    if print_logs:
        import logging
        import sys
        consolehandler = logging.StreamHandler(sys.stdout)
        consolehandler.setLevel(logging.DEBUG)
        logger.addHandler(consolehandler)

    if print_logs:
        print_table_header()
    for username in sorted(instance_map.keys()):
        instances = instance_map[username]
        monitor_instances_for_user(provider, username, instances,
                                    print_logs, end_date)
    logger.info("Monitoring completed")
    if print_logs:
        logger.removeHandler(consolehandler)


def monitor_instances_for_user(provider, username, instances,
                               print_logs=False, end_date=None):
    """
    """
    from core.models import IdentityMembership
    try:
        #Note: This username may or may not have an associated
        #Allocation/IdentityMembership
        user = AtmosphereUser.objects.get(username=username)
    except AtmosphereUser.DoesNotExist:
        #if instances:
        #    logger.warn("WARNING: User %s has %s instances, but does not"
        #                "exist on this database" % (username, len(instances)))
        return
    for identity in user.identity_set.filter(provider=provider):
        try:
            identity_id = identity.id
            #GATHER STATISTICS FIRST
            #This will be: Calculate time for all instances within a
            #given delta, including the instances listed currently.
            time_period = settings.FIXED_WINDOW
            allocation = get_allocation(username, identity_id)
            delta_time = get_delta(allocation, time_period, end_date)
            time_used, instance_status_map = current_instance_time(
                user, instances,
                identity_id, delta_time, end_date)
            import ipdb;ipdb.set_trace()
            if print_logs:
                print_table_row(instance_status_map, user,
                                allocation, time_used)
                return
            over_allocation = enforce_allocation(identity, user, time_used)
            if over_allocation:
                print_instances(instance_status_map, user, allocation, time_used)
        except IdentityMembership.DoesNotExist:
            pass
            #if instances:
            #    logger.warn(
            #        "WARNING: User %s has %s instances, but does not"
            #        "exist on this database" % (username, len(instances)))
        except:
            logger.exception("Unable to monitor Identity:%s"
                             % (identity,))


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


def enforce_allocation(identity, user, time_used):
    from core.models.instance import convert_esh_instance
    #TODO: When user->group is no longer true,
    #TODO: Is 'group' allowed to use this identity?
    #group = Group.objects.get(name=user.username)
    #im = identity.identitymembership_set.get(member=group)
    allocation = get_allocation(user.username, identity.id)
    if not allocation:
        logger.info("%s has NO allocation. Returning.." %
                (user.username, ))
        return False
    max_time_allowed = timedelta(minutes=allocation.threshold)
    time_diff = max_time_allowed - time_used
    over_allocated = time_diff.total_seconds() <= 0
    if not over_allocated:
        logger.info("%s is NOT OVER their allocation. Returning.." %
                (user.username, ))
        return False
    if not settings.ENFORCING:
        logger.info('Settings dictate allocations are NOT enforced')
        return False
    logger.info("%s is OVER their allowed allocation by %s" %
                (user.username, time_diff))
    driver = get_esh_driver(identity)
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

