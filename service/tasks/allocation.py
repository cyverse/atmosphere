from datetime import timedelta
from django.utils import timezone

from api import get_esh_driver
from core.models import Instance, Identity
from core.models.instance import map_to_identity
from service.allocation import check_allocation

from threepio import logger

def suspend_over_quota_task(driver, username, identity_id, *args, **kwargs):
    if check_allocation(username, identity_id)\
            and hasattr(driver, 'suspend_instance'):
        for instance in driver.list_instances():
            driver.suspend_instance(instance)

def monitor_instances():
    #TODO: Combine all of these functions
    #1. End-date missing instances (They were terminated)
    #2. Update status of instances who dont have matching last_history
    #3. Handling instances that dont exist yet (Is this a valid use case?)
    pass

def correct_missing_instances():
    #These instances are running or missing
    core_instances = Instance.objects.filter(end_date=None)

    #1. Optimize: Get list of instances to be tested for each ID
    instance_identity_map = map_to_identity(core_instances)

    #2. For each Identity, build the driver, check the instance_list
    for identity_id, instance_list in instance_identity_map.iteritems():
        identity = Identity.objects.get(id=identity_id)
        driver = get_esh_driver(identity)
        existing_list = driver.list_instances()
        existing_ids = [instance.id for instance in existing_list]
        dead_instances = [instance for instance in instance_list \
                          if instance.provider_alias not in existing_ids]
        if not dead_instances:
            continue
        logger.info("Adding enddate to %s for %s" %
                ([i.provider_alias for i in dead_instances], identity))
        for instance in dead_instances:
            instance.end_date_all()

def check_build_instances():
    ish_list = InstanceStatusHistory.objects.filter(
            status__name='build',
            end_date=None)

    instances = [ish.instance for ish in ish_list]
    instance_identity_map = map_to_identity(instances)

    for identity_id, instance_list in instance_identity_map.iteritems():
        identity = Identity.objects.get(id=identity_id)
        driver = get_esh_driver(identity)
        esh_instances = driver.list_instances()
        id_list = [core_i.provider_alias for core_i in instance_list]
        for instance in instance_list:
            if instance.id not in id_list:
                #Instance was destroyed, end-date instance & status
                instance.end_date_all()
            instance.update_status(instance.status, instance.extra.get('task'))
    

