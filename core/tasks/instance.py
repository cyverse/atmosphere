from datetime import datetime

from django.conf import settings

from celery.decorators import periodic_task
from celery.task.schedules import crontab

from threepio import logger



@periodic_task(run_every=crontab(hour='*', minute='*/15', day_of_week='*'),
               time_limit=120, retry=1)  # 2min timeout
def test_all_instance_links():
    try:
        logger.debug("test_all_instance_links task started at %s." %
                     datetime.now())
        instances = get_all_instances()
        update_links(instances)
        logger.debug("test_all_instance_links task finished at %s." %
                     datetime.now())
    except Exception as exc:
        logger.exception('Error during test_all_instance_links task')
        test_all_instance_links.retry(exc=exc)


def get_all_instances():
    from core.models import Identity, Provider
    from api import get_esh_driver
    from service.driver import get_admin_driver
    all_instances = []
    for provider in Provider.objects.all():
        try:
            admin_driver = get_admin_driver(provider)
            if not admin_driver:
                raise Exception("No account admins for provider %s"
                                % provider)
            meta_driver = admin_driver.meta(admin_driver=admin_driver)
            all_instances.extend(meta_driver.all_instances())
        except:
            logger.exception("Problem accessing all "
                             "instances for provider: %s" % provider)
    return all_instances


def active_instances(instances):
    tested_instances = {}
    for instance in instances:
        results = test_instance_links(instance.alias, instance.ip)
        tested_instances.update(results)
    return tested_instances


def test_instance_links(alias, uri):
    from rtwo.linktest import test_link
    if uri is None:
        return {alias: {'vnc': False, 'shell': False}}
    shell_address = '%s/shell/%s/' % (settings.SERVER_URL, uri)
    try:
        shell_success = test_link(shell_address)
    except Exception, e:
        logger.exception("Bad shell address: %s" % shell_address)
        shell_success = False
    vnc_address = 'http://%s:5904' % uri
    try:
        vnc_success = test_link(vnc_address)
    except Exception, e:
        logger.exception("Bad vnc address: %s" % vnc_address)
        vnc_success = False
    return {alias: {'vnc': vnc_success, 'shell': shell_success}}


def update_links(instances):
    from core.models import Instance
    updated = []
    linktest_results = active_instances(instances)
    for (instance_id, link_results) in linktest_results.items():
        try:
            update = False
            instance = Instance.objects.get(provider_alias=instance_id)
            if link_results['shell'] != instance.shell:
                logger.debug('Change Instance %s shell %s-->%s' %
                             (instance, instance.shell,
                              link_results['shell']))
                instance.shell = link_results['shell']
                update = True
            if link_results['vnc'] != instance.vnc:
                logger.debug('Change Instance %s VNC %s-->%s' %
                             (instance, instance.vnc,
                              link_results['vnc']))
                instance.vnc = link_results['vnc']
                update = True
            if update:
                instance.save()
                updated.append(instance)
        except Instance.DoesNotExist:
            continue
    logger.debug("Instances updated: %d" % len(updated))
    return updated
