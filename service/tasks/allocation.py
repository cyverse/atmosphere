import time

from datetime import timedelta
from dateutil.relativedelta import relativedelta

from django.utils import timezone
from django.conf import settings

from celery.decorators import task
from celery.task.schedules import crontab

from core.models.group import Group
from core.models.user import AtmosphereUser
from core.models.provider import Provider

from service.allocation import check_over_allocation, current_instance_time,\
get_delta, get_allocation
from service.driver import get_admin_driver

from threepio import logger


@task(name="monitor_instances")
def monitor_instances():
    """
    Update instances for each active provider.
    """
    for p in Provider.get_active():
        monitor_instances_for(p)


def get_instance_owner_map(provider, users=None):
    """
    All keys == All identities
    """
    admin_driver = get_admin_driver(provider)
    meta = admin_driver.meta(admin_driver=admin_driver)

    all_identities = _select_identities(provider, users)

    all_instances = meta.all_instances()
    all_tenants = admin_driver._connection._keystone_list_tenants()
    #Convert instance.owner from tenant-id to tenant-name all at once
    all_instances = _convert_tenant_id_to_names(all_instances, all_tenants)
    #Make a mapping of owner-to-instance
    instance_map = _make_instance_owner_map(all_instances, users=users)
    logger.info("Instance owner map created")
    identity_map = _include_all_idents(all_identities, instance_map)
    logger.info("Identity map created")
    return identity_map

def monitor_instances_for(provider, users=None, print_logs=False):
    """
    Update instances for provider.
    """
    #For now, lets just ignore everything that isn't openstack.
    if 'openstack' not in provider.type.name.lower():
        return

    instance_map = get_instance_owner_map(provider, users=users)

    if print_logs:
        import logging, sys
        consolehandler = logging.StreamHandler(sys.stdout)
        consolehandler.setLevel(logging.DEBUG)
        logger.addHandler(consolehandler)

    for username in instance_map.keys():
        instances = instance_map[username]
        monitor_instances_for_user(provider, username, instances)
    logger.info("Monitoring completed")
    if print_logs:
        logger.removeHandler(consolehandler)

def monitor_instances_for_user(provider, username, instances):
    from core.models.instance import convert_esh_instance
    try:
        user = AtmosphereUser.objects.get(username=username)
    except AtmosphereUser.DoesNotExist:
        if instances:
            logger.warn("WARNING: User %s has %s instances, but does not"
            "exist on this database" % username, len(instances))
        return
    for identity in user.identity_set.filter(provider=provider):
        try:
            identity_id = identity.id
            #GATHER STATISTICS FIRST
            #This will be: Calculate time that user has used all instances within a
            #given delta, including the instances listed currently.
            time_period=relativedelta(day=1, months=1)
            allocation = get_allocation(username, identity_id)
            delta_time = get_delta(allocation, time_period)
            time_used = current_instance_time(
                    user, instances,
                    identity_id, delta_time)
            enforce_allocation(identity, user, time_used)
        except:
            logger.exception("Unable to monitor Identity:%s"
                         % (identity,))

    
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
        if i.owner not in users:
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
    #TODO: When user->group is no longer true,
    # we will need to modify this..
    group = Group.objects.get(name=user.username)
    im = identity.identitymembership_set.get(member=group)
    allocation = get_allocation(user.username, identity.id)
    if not allocation:
        return False
    max_time_allowed = timedelta(minutes=allocation.threshold)
    time_diff = max_time_allowed - time_used
    over_allocated = time_diff.total_seconds() <= 0
    if not over_allocated:
        return False
    if settings.DEBUG:
        logger.info('Do not enforce allocations in DEBUG mode')
        return False
    logger.info("%s is OVER their allowed quota by %s" %
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
    return True # User was over_allocation


def update_instances(driver, identity, esh_list, core_list):
    """
    End-date core instances that don't show up in esh_list
    && Update the values of instances that do
    """
    esh_ids = [instance.id for instance in esh_list]
    #logger.info('%s Instances for Identity %s: %s' % (len(esh_ids), identity, esh_ids))
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
        core_size = convert_esh_size(esh_size, provider_id)
        core_instance.update_history(
            esh_instance.extra['status'],
            core_size,
            esh_instance.extra.get('task') or
            esh_instance.extra.get(
                'metadata', {}).get('tmp_status'))
    return
