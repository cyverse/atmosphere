from celery.decorators import task
from celery.task.schedules import crontab

from django.utils.timezone import datetime
from rtwo.exceptions import NeutronClientException, NeutronException

from threepio import celery_logger

from core.models import AtmosphereUser as User
from core.models import Provider,Identity, Credential

from service.driver import get_account_driver


@task(name="remove_empty_networks_for")
def remove_empty_networks_for(provider_id):
    provider = Provider.objects.get(id=provider_id)
    os_driver = get_account_driver(provider)
    all_instances = os_driver.admin_driver.list_all_instances()
    project_map = os_driver.network_manager.project_network_map()
    known_project_names = Credential.objects.filter(
        key='ex_project_name').values_list('value',flat=True)
    projects_with_networks = sorted([k for k in project_map.keys() if k in known_project_names])
    for project in projects_with_networks:
        networks = project_map[project]['network']
        if not isinstance(networks, list):
            networks = [networks]
        for network in networks:
            network_name = network['name']
            celery_logger.debug("Checking if network %s is in use" % network_name)
            if running_instances(network_name, all_instances):
                continue
            user = project
            identity = Identity.objects.filter(provider_id=provider_id, credential__key='ex_project_name', credential__value=project).filter(credential__key='key', credential__value=user).first()
            if not identity:
                celery_logger.warn("NOT Removing project network for User:%s, Project:%s -- No Valid Identity found!"
                             % (user, project))
                continue
            try:
                celery_logger.debug("Removing project network for User:%s, Project:%s"
                             % (user, project))
                os_driver.delete_user_network(identity)
            except NeutronClientException:
                celery_logger.exception("Neutron unable to remove project"
                                 "network for %s-%s" % (user, project))
            except NeutronException:
                celery_logger.exception("Neutron unable to remove project"
                                 "network for %s-%s" % (user, project))


@task(name="remove_empty_networks")
def remove_empty_networks():
    celery_logger.debug("remove_empty_networks task started at %s." %
                 datetime.now())
    for provider in Provider.get_active(type_name='openstack'):
        remove_empty_networks_for.apply_async(args=[provider.id])


def running_instances(network_name, all_instances):
    for instance in all_instances:
        if network_name in instance.extra['addresses'].keys():
            #    #If not build/active, the network is assumed to be NOT in use
            celery_logger.debug("Network %s is in use, Active Instance:%s"
                         % (network_name, instance.id))
            return True
    celery_logger.debug("Network %s is NOT in use" % network_name)
    return False
