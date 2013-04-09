"""
"""
from celery.task import task

from atmosphere.logger import logger

#from core.synchronize import
from core.models.instance import Instance
from core.models.volume import Volume

from datetime import timedelta, datetime


@task()
def sync():
    logger.debug("Syncing Resources...")

