from datetime import timedelta
from dateutil.relativedelta import relativedelta

from django.utils import timezone

from celery.task import periodic_task
from celery.task.schedules import crontab

from core.models.group import Group
from core.models.user import AtmosphereUser
from core.models.provider import Provider

from service.allocation import check_over_allocation
from service.driver import get_admin_driver

from threepio import logger


@periodic_task(run_every=crontab(hour='*', minute='*/15', day_of_week='*'),
               # 5min before task expires, 5min to run task
               expires=5*60, time_limit=5*60, retry=0)
def monitor_instances():
    """
    Update instances for each active provider.
    """
    for p in Provider.objects.filter(active=True, end_date=None):
        monitor_instances_for(p)


def get_instance_owner_map(provider):
    admin_driver = get_admin_driver(provider)
    meta = admin_driver.meta(admin_driver=admin_driver)
    logger.info("Retrieving all tenants..")
    all_tenants = admin_driver._connection._keystone_list_tenants()
    logger.info("Retrieved %s tenants. Retrieving all instances.."
                % len(all_tenants))
    all_instances = meta.all_instances()
    logger.info("Retrieved %s instances." % len(all_instances))
    #Convert tenant-id to tenant-name all at once
    all_instances = _convert_tenant_id_to_names(all_instances, all_tenants)
    logger.info("Owner information added.")
    #Make a mapping of owner-to-instance
    instance_map = _make_instance_owner_map(all_instances)
    logger.info("Instance owner map created")
    return instance_map

def monitor_instances_for(provider):
    """
    Update instances for provider.
    """
    #For now, lets just ignore everything that isn't openstack.
    if 'openstack' not in provider.type.name.lower():
        return
    instance_map = get_instance_owner_map(provider)
    for username in instance_map.keys():
        try:
            user = AtmosphereUser.objects.get(username=username)
            group = Group.objects.get(name=user.username)
            id = user.identity_set.get(provider=provider)
            im = id.identitymembership_set.get(member=group)
            if not im.allocation:
                continue
            instances = instance_map[username]
            over_allocation = over_allocation_test(im.identity, instances)
            if over_allocation:
                continue
            core_instances = im.identity.instance_set.filter(end_date=None)
            update_instances(im.identity, instances, core_instances)
        except:
            logger.exception("Unable to monitor User:%s" % username)
            raise
    logger.info("Monitoring completed")

def _make_instance_owner_map(instances):
    owner_map = {}
    for i in instances:
        key = i.owner
        instance_list = owner_map.get(key, [])
        instance_list.append(i)
        owner_map[key] = instance_list
    return owner_map


def _convert_tenant_id_to_names(instances, tenants):
    for i in instances:
        for tenant in tenants:
            if tenant['id'] == i.owner:
                i.owner = tenant['name']
    return instances

def over_allocation_test(identity, esh_instances):
    from api import get_esh_driver
    from core.models.instance import convert_esh_instance
    from atmosphere import settings
    over_allocated, time_diff = check_over_allocation(
        identity.created_by.username, identity.id,
        time_period=relativedelta(day=1, months=1))
    if not over_allocated:
        # Nothing changed, bail.
        return False
    if settings.DEBUG:
        logger.info('Do not enforce allocations in DEBUG mode')
        return False
    driver = get_esh_driver(identity)
    for instance in esh_instances:
        #Suspend active instances, update the task in the DB
        try:
            if driver._is_active_instance(instance):
                driver.suspend_instance(instance)
        except Exception, e:
            if 'in vm_state suspended' not in e.message:
                raise
        updated_esh = driver.get_instance(instance.id)
        updated_core = convert_esh_instance(driver, updated_esh,
                                            identity.provider.id,
                                            identity.id,
                                            identity.created_by)
        updated_core.update_history(updated_esh.extra['status'],
                                    updated_esh.extra.get('task'))
    #All instances are dealt with, move along.
    return True # User was over_allocation


def update_instances(identity, esh_list, core_list):
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
        core_instance.update_history(
            esh_instance.extra['status'],
            esh_instance.extra.get('task') or
            esh_instance.extra.get('metadata', {}).get('tmp_status'))
    return
