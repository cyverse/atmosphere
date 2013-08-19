from datetime import timedelta
from django.utils import timezone

from api import getEshDriver
from core.models import Instance, Identity
from core.models.instance import map_to_identity
from service.allocation import get_time, get_allocation

from threepio import logger

def suspend_over_quota_task(driver, username, identity_id, *args, **kwargs):
    if check_over_quota_task(username, identity_id)\
            and hasattr(driver, 'suspend_instance'):
        for instance in driver.list_instances():
            driver.suspend_instance(instance)

def correct_missing_instances():
    core_instances = Instance.objects.filter(end_date=None)
    #1. Optimize: Get list of instances to be tested for each ID
    instance_id_map = map_to_identity(core_instances)
    #2. For each Identity, build the driver, check the instance_list
    for identity_id, instance_list in instance_id_map.iteritems():
        identity = Identity.objects.get(id=identity_id)
        driver = getEshDriver(identity)
        existing_list = driver.list_instances()
        existing_ids = [instance.id for instance in existing_list]
        dead_instances = [instance for instance in instance_list \
                          if instance.provider_alias not in existing_ids]
        if not dead_instances:
            continue
        logger.info("Adding enddate to %s for %s" %
                ([i.provider_alias for i in dead_instances], identity))
        for instance in dead_instances:
            instance.end_date = timezone.now()
            instance.save()
