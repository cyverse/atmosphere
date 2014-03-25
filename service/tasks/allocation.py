from datetime import timedelta
from dateutil.relativedelta import relativedelta

from django.utils import timezone

from celery.decorators import task
from celery.task.schedules import crontab

from core.models.group import Group
from core.models.user import AtmosphereUser
from core.models.provider import Provider

from service.allocation import check_over_allocation
from service.driver import get_admin_driver

from threepio import logger


@task(name="monitor_instances")
def monitor_instances():
    """
    Update instances for each active provider.
    """
    for p in Provider.get_active():
        monitor_instances_for(p)


def get_instance_owner_map(provider):
    """
    All keys == All identities
    """
    admin_driver = get_admin_driver(provider)
    meta = admin_driver.meta(admin_driver=admin_driver)
    all_identities = provider.identity_set.all()
    logger.info("Retrieving all tenants..")
    all_tenants = admin_driver._connection._keystone_list_tenants()
    logger.info("Retrieved %s tenants. Retrieving all instances.."
                % len(all_tenants))
    all_instances = meta.all_instances()
    logger.info("Retrieved %s instances." % len(all_instances))
    #Convert instance.owner from tenant-id to tenant-name all at once
    all_instances = _convert_tenant_id_to_names(all_instances, all_tenants)
    logger.info("Owner information added.")
    #Make a mapping of owner-to-instance
    instance_map = _make_instance_owner_map(all_instances)
    logger.info("Instance owner map created")
    identity_map = _include_all_idents(all_identities, instance_map)
    logger.info("Identity map created")
    return identity_map

def monitor_instances_for(provider):
    """
    Update instances for provider.
    """
    #For now, lets just ignore everything that isn't openstack.
    if 'openstack' not in provider.type.name.lower():
        return
    instance_map = get_instance_owner_map(provider)
    for username in instance_map.keys():
        instances = instance_map[username]
        monitor_instances_for_user(provider, username, instances)
    logger.info("Monitoring completed")

def monitor_instances_for_user(provider, username, instances):
    try:
        import ipdb;ipdb.set_trace()
        user = AtmosphereUser.objects.get(username=username)
        #TODO: When user->group is no longer true,
        # we will need to modify this..
        group = Group.objects.get(name=user.username)
        ident = user.identity_set.get(provider=provider)
        im = ident.identitymembership_set.get(member=group)
        over_allocation = over_allocation_test(im.identity,
                                               instances)
        core_instances = user.instance_set.filter(
                provider_machine__provider=provider,
                end_date=None)
        core_instances_ident = ident.instance_set.filter(end_date=None)
        update_instances(im.identity, instances, core_instances)
    except:
        logger.exception("Unable to monitor User:%s on Provider:%s"
                         % (username,provider))

    
def _include_all_idents(identities, owner_map):
    #Include all identities with 0 instances to the monitoring
    identity_owners = [ident.get_credential('ex_tenant_name')
                       for ident in identities]
    owners_w_instances = owner_map.keys()
    for user in identity_owners:
        if user not in owners_w_instances:
            owner_map[user] = []
    return owner_map

def _make_instance_owner_map(instances):
    owner_map = {}
    for i in instances:
        key = i.owner
        instance_list = owner_map.get(key, [])
        instance_list.append(i)
        owner_map[key] = instance_list
    return owner_map


def _convert_tenant_id_to_names(instances, tenants):
    for i in instances:
        for tenant in tenants:
            if tenant['id'] == i.owner:
                i.owner = tenant['name']
    return instances

def over_allocation_test(identity, esh_instances):
    from api import get_esh_driver
    from core.models.instance import convert_esh_instance
    from atmosphere import settings
    over_allocated, time_diff = check_over_allocation(
        identity.created_by.username, identity.id,
        time_period=relativedelta(day=1, months=1))
    logger.info("Overallocation Test: %s - %s - %s\tInstances:%s"
                % (identity.created_by.username, over_allocated, time_diff, esh_instances))
    if not over_allocated:
        # Nothing changed, bail.
        return False
    if settings.DEBUG:
        logger.info('Do not enforce allocations in DEBUG mode')
        return False
    driver = get_esh_driver(identity)
    running_instances = []
    for instance in esh_instances:
        #Suspend active instances, update the task in the DB
        try:
            if driver._is_active_instance(instance):
                driver.suspend_instance(instance)
        except Exception, e:
            if 'in vm_state suspended' not in e.message:
                raise
        updated_esh = driver.get_instance(instance.id)
        updated_core = convert_esh_instance(driver, updated_esh,
                                            identity.provider.id,
                                            identity.id,
                                            identity.created_by)
        updated_core.update_history(updated_esh.extra['status'],
                                    updated_esh.extra.get('task'))
        running_instances.append(updated_core)
    #All instances are dealt with, move along.
    return True # User was over_allocation


def update_instances(identity, esh_list, core_list):
    """
    End-date core instances that don't show up in esh_list
    && Update the values of instances that do
    """
    esh_ids = [instance.id for instance in esh_list]
    #logger.info('%s Instances for Identity %s: %s' % (len(esh_ids), identity, esh_ids))
    for core_instance in core_list:
        try:
            index = esh_ids.index(core_instance.provider_alias)
        except ValueError:
            logger.info("Did not find instance %s in ID List: %s" %
                        (core_instance.provider_alias, esh_ids))
            core_instance.end_date_all()
            continue
        esh_instance = esh_list[index]
        core_instance.update_history(
            esh_instance.extra['status'],
            esh_instance.extra.get('task') or
            esh_instance.extra.get('metadata', {}).get('tmp_status'))
    return
