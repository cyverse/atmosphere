from datetime import datetime

from celery.decorators import task

from atmosphere.logger import logger


@task()
def deploy_instance(driver, *args, **kwargs):
    logger.debug("deploy_instance task started at %s." % datetime.now())
    driver.deploy_instance(*args, **kwargs)
    logger.debug("deploy_instance task finished at %s." % datetime.now())
