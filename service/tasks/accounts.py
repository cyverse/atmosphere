from celery.decorators import task
from celery.task.schedules import crontab

from django.utils.timezone import datetime
from neutronclient.common.exceptions import NeutronException, NeutronClientException

from threepio import logger

from core.models import AtmosphereUser as User
from core.models import Provider

from service.accounts.openstack import AccountDriver as OSAccountDriver


@task(name="remove_empty_networks")
def remove_empty_networks():
    try:
        logger.debug("remove_empty_networks task started at %s." %
                     datetime.now())
        for provider in Provider.get_active(type_name='openstack'):
            os_driver = OSAccountDriver(provider)
            all_instances = os_driver.admin_driver.list_all_instances()
            project_map = os_driver.network_manager.project_network_map()
            projects_with_networks = project_map.keys()
            for project in projects_with_networks:
                network_name = project_map[project]['network']['name']
                logger.debug("Checking if network %s is in use" % network_name)
                if running_instances(network_name, all_instances):
                    continue
                #TODO: Will change when not using 'usergroups' explicitly.
                user = project
                try:
                    logger.debug("Removing project network for User:%s, Project:%s"
                                 % (user, project))
                    os_driver.network_manager.delete_project_network(user, project)
                except NeutronClientException:
                    logger.exception("Neutron unable to remove project"
                                     "network for %s-%s" % (user,project))
                except NeutronException:
                    logger.exception("Neutron unable to remove project"
                                     "network for %s-%s" % (user,project))
    except Exception as exc:
        logger.exception("Failed to run remove_empty_networks")


def running_instances(network_name, all_instances):
    for instance in all_instances:
        if network_name in instance.extra['addresses'].keys():
            logger.debug("Network %s is in use" % network_name)
            return True
    logger.debug("Network %s is NOT in use" % network_name)
    return False
