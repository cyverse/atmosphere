from datetime import datetime

from celery.decorators import task
from celery import chain

from atmosphere.logger import logger


@task(name="deploy_to", max_retries=2, default_retry_delay=120, ignore_result=True)
def deploy_to(driverCls, provider, identity, instance, *args, **kwargs):
    try:
        logger.debug("deploy_to task started at %s." % datetime.now())
        from service import compute
        compute.initialize()
        driver = driverCls(provider, identity)
        driver.deploy_init_to(instance, *args, **kwargs)
        logger.debug("deploy_to task finished at %s." % datetime.now())
    except Exception as exc:
        logger.warn(exc)
        deploy_to.retry(exc=exc)


@task(name="deploy_init_to",
      countdown=20,
      default_retry_delay=60,
      ignore_result=True,
      max_retries=1)
def deploy_init_to(driverCls, provider, identity, instance_id, *args, **kwargs):
    try:
        logger.debug("deploy_init_to task started at %s." % datetime.now())
        from service import compute
        compute.initialize()
        driver = driverCls(provider, identity)
        logger.debug(provider)
        logger.debug(identity)
        logger.debug(driver.list_instances())
        instance = driver.get_instance(instance_id)
        logger.debug(instance)
        if not instance.ip:
            chain(add_floating_ip.si(driverCls,
                                     provider,
                                     identity,
                                     instance_id),
                  _deploy_init_to.si(driverCls,
                                     provider,
                                     identity,
                                     instance_id)).apply_async()
        else:
            _deploy_init_to.delay(driverCls,
                                  provider,
                                  identity,
                                  instance_id,
                                  *args, **kwargs)
        logger.debug("deploy_init_to task finished at %s." % datetime.now())
    except Exception as exc:
        logger.warn(exc)
        deploy_init_to.retry(exc=exc)


@task(name="_deploy_init_to",
      default_retry_delay=120,
      ignore_result=True,
      max_retries=2)
def _deploy_init_to(driverCls, provider, identity, instance_id):
    try:
        logger.debug("_deploy_init_to task started at %s." % datetime.now())
        #logger.debug("_deploy_init_to %s" % driverCls)
        #logger.debug("_deploy_init_to %s" % provider)
        #logger.debug("_deploy_init_to %s" % identity)
        #logger.debug("_deploy_init_to %s" % args)
        #logger.debug("_deploy_init_to %s" % kwargs)
        from service import compute
        compute.initialize()
        driver = driverCls(provider, identity)
        instance = driver.get_instance(instance_id)
        driver.deploy_init_to(instance)
        logger.debug("_deploy_init_to task finished at %s." % datetime.now())
    except Exception as exc:
        logger.warn(exc)
        _deploy_init_to.retry(exc=exc)


@task(name="add_floating_ip",
      default_retry_delay=15,
      ignore_result=True,
      max_retries=6)
def add_floating_ip(driverCls, provider, identity, instance_alias, *args, **kwargs):
    try:
        logger.debug("add_floating_ip task started at %s." % datetime.now())
        from service import compute
        compute.initialize()
        driver = driverCls(provider, identity)
        instance = driver.get_instance(instance_alias)
        if not instance.ip:
            driver._add_floating_ip(instance_alias, *args, **kwargs)
        else:
            logger.debug("public ip already found! %s" % instance.ip)
        logger.debug("add_floating_ip task finished at %s." % datetime.now())
    except Exception as exc:
        add_floating_ip.retry(exc=exc)
