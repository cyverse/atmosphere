from datetime import timedelta

from django.utils import timezone

from celery.task import periodic_task
from celery.task.schedules import crontab

from core.models.group import Group
from core.models.provider import Provider

from service.allocation import check_over_allocation
from service.driver import get_admin_driver

from threepio import logger


@periodic_task(run_every=crontab(hour='*', minute='*/15', day_of_week='*'),
               time_limit=120, retry=0)
def monitor_instances():
    """
    Update instances for each active provider.
    """
    for p in Provider.objects.filter(active=True, end_date=None):
        monitor_instances_for(p)


def monitor_instances_for(provider):
    """
    Update instances for provider.
    """
    admin_driver = get_admin_driver(provider)
    meta = admin_driver.meta(admin_driver=admin_driver)
    instances = meta.all_instances()
    for i in instances:
        try:
            user = User.objects.get(username=i.extra["metadata"]["creator"])
            group = Group.objects.get(name=user.username)
            id = user.identity_set.get(provider=p)
            im = id.identitymembership_set.get(member=group)
            if not im.allocation:
                continue
            over_allocation = over_allocation_test(im.identity, i)
            if over_allocation:
                continue
            core_instances = im.identity.instance_set.filter(end_date=None)
            update_instances(im.identity, i, core_instances)
        except:
            logger.info("Unable to monitor instance: %s" % i)


def over_allocation_test(identity, esh_instances):
    from api import get_esh_driver
    from core.models.instance import convert_esh_instance
    from atmosphere import settings
    over_allocated, time_diff = check_over_allocation(
        identity.created_by.username, identity.id)
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
    logger.info('Instances for Identity %s: %s' % (identity, esh_ids))
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
