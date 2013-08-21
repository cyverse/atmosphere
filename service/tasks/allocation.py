from datetime import timedelta
from django.utils import timezone

from api import get_esh_driver
from core.models import Instance, Identity
from core.models.instance import map_to_identity
from service.allocation import check_allocation

from threepio import logger

def over_allocation_test(identity, esh_instances):
    if check_allocation(identity.created_by.username, identity.id):
        return False # Nothing changed

    #ASSERT:Over the allocation, suspend all instances for the identity

    #TODO: It may be beneficial to only suspend if: 
    # instance.created_by == im.member.name
    # (At this point, it doesnt matter)

    driver = get_esh_driver(im.identity)
    for instance in esh_instances:
        #Suspend, get updated status/task, and update the DB
        driver.suspend_instance(instance)
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
    for core_instance in core_list:
        try:
            index = esh_ids.index(core_instance.provider_alias)
        except ValueError:
            core_instance.end_date_all()
            continue
        esh_instance = esh_list[index]
        core_instance.update_history(
            esh_instance.extra['status'],
            esh_instance.extra.get('task') or\
            esh_instance.extra.get('metadata',{}).get('tmp_status'))
    return

def monitor_instances():
    """
    This task should be run every 5m-15m
    """
    for im in IdentityMembership.objects.all():
        core_instances = im.identity.instance_set.filter(end_date=None)
        if not core_instances:
            continue
        driver = get_esh_driver(im.identity)
        esh_instances = driver.list_instances()

        instances_suspended = over_allocation_test(im.identity, esh_instances)
        if instances_suspended:
            continue
        update_instances(im.identity, esh_instances, core_instances)
