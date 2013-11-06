from datetime import timedelta
from django.utils import timezone
from celery.task import periodic_task
from celery.task.schedules import crontab

from core.models import Instance, IdentityMembership
from core.models.instance import convert_esh_instance
from service.allocation import check_over_allocation

from threepio import logger

@periodic_task(run_every=crontab(hour='*', minute='*/15', day_of_week='*'),
               time_limit=120, retry=0) # 2min timeout
def monitor_instances():
    """
    This task should be run every 5m-15m
    """
    from api import get_esh_driver
    for im in IdentityMembership.objects.all():
        #Start by checking for running/missing instances
        core_instances = im.identity.instance_set.filter(end_date=None)
        if not core_instances:
            continue

        #Running/missing instances found. We may have to do something!
        driver = get_esh_driver(im.identity)
        esh_instances = driver.list_instances()

        #We may need to update instance status history
        update_instances(im.identity, esh_instances, core_instances)

        #Test allocation && Suspend instances if we are over allocated time
        over_allocation = over_allocation_test(im.identity, esh_instances)
        if over_allocation:
            continue


def over_allocation_test(identity, esh_instances):
    from api import get_esh_driver
    over_allocated, time_diff = check_over_allocation(identity.created_by.username, identity.id)
    if not over_allocated:
        # Nothing changed, bail.
        return False

    #NOTE: For this roll out, allocations will NOT auto-suspend when the user has expired
    return True

    #ASSERT:Over the allocation, suspend all instances for the identity

    #TODO: It may be beneficial to only suspend if: 
    # instance.created_by == im.member.name
    # (At this point, it doesnt matter)

    driver = get_esh_driver(identity)
    for instance in esh_instances:
        #Suspend, get updated status/task, and update the DB
        try:
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
    logger.info(esh_ids)
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
            esh_instance.extra.get('task') or\
            esh_instance.extra.get('metadata',{}).get('tmp_status'))
    return
