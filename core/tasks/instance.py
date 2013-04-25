from celery.decorators import periodic_task
from celery.task.schedules import crontab

from atmosphere.logger import logger

@periodic_task(run_every=crontab(hour='*', minute='*/5', day_of_week='*'))
def test_all_instance_links():
    try:
        from core.models import Identity, Provider, Instance
        from api import getEshDriver
        from service.linktest import active_instances
        from datetime import datetime
        logger.debug("test_all_instance_links task started at %s." % datetime.now())
        all_instances = []
        for provider in Provider.objects.all():
            identity_list = Identity.objects.filter(provider=provider)
            if not identity_list:
                continue
            identity = identity_list[0]
            driver = getEshDriver(identity)
            meta_driver = driver.provider.metaCls(driver)
            all_instances.extend(meta_driver.all_instances())
        linktest_results = active_instances(all_instances)
        for (instance_id, link_results) in linktest_results.items():
            try:
                instance = Instance.objects.get(provider_alias=instance_id)
                instance.shell = link_results['shell']
                instance.vnc = link_results['vnc']
                instance.save()
            except Instance.DoesNotExist:
                continue
        logger.debug("test_all_instance_links task finished at %s." % datetime.now())
    except Exception as exc:
        logger.warn(exc)
        test_all_instance_links.retry(exc=exc)
