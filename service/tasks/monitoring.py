import time
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from django.conf import settings

from celery.decorators import task

from core.query import only_current
from core.models.group import Group, IdentityMembership
from core.models.size import Size, convert_esh_size
from core.models.instance import convert_esh_instance, Instance
from core.models.user import AtmosphereUser
from core.models.provider import Provider

from service.monitoring import\
        _cleanup_missing_instances,\
        _get_instance_owner_map, \
        _get_identity_from_tenant_name
from service.monitoring import user_over_allocation_enforcement
from service.cache import get_cached_driver, get_cached_instances

from threepio import logger


def strfdelta(tdelta, fmt=None):
    from string import Formatter
    if not fmt:
        #The standard, most human readable format.
        fmt = "{D} days {H:02} hours {M:02} minutes {S:02} seconds"
    if tdelta == timedelta():
        return "0 minutes"
    formatter = Formatter()
    return_map = {}
    div_by_map = {'D': 86400, 'H': 3600, 'M': 60, 'S': 1}
    keys = map(lambda x: x[1], list(formatter.parse(fmt)))
    remainder = int(tdelta.total_seconds())

    for unit in ('D', 'H', 'M', 'S'):
        if unit in keys and unit in div_by_map.keys():
            return_map[unit], remainder = divmod(remainder, div_by_map[unit])

    return formatter.format(fmt, **return_map)


def strfdate(datetime_o, fmt=None):
    if not fmt:
        #The standard, most human readable format.
        fmt = "%m/%d/%Y %H:%M:%S"
    if not datetime_o:
        datetime_o = timezone.now()

    return datetime_o.strftime(fmt)


@task(name="monitor_instances")
def monitor_instances():
    """
    Update instances for each active provider.
    """
    for p in Provider.get_active():
        monitor_instances_for.apply_async(args=[p.id])


@task(name="monitor_instances_for")
def monitor_instances_for(provider_id, users=None,
                          print_logs=False, start_date=None, end_date=None):
    """
    Run the set of tasks related to monitoring instances for a provider.
    Optionally, provide a list of usernames to monitor
    While debugging, print_logs=True can be very helpful.
    start_date and end_date allow you to search a 'non-standard' window of time.
    """
    provider = Provider.objects.get(id=provider_id)

    #For now, lets just ignore everything that isn't openstack.
    if 'openstack' not in provider.type.name.lower():
        return

    instance_map = _get_instance_owner_map(provider, users=users)

    if print_logs:
        import logging
        import sys
        consolehandler = logging.StreamHandler(sys.stdout)
        consolehandler.setLevel(logging.DEBUG)
        logger.addHandler(consolehandler)

    #DEVNOTE: Potential slowdown running multiple functions
    #Break this out when instance-caching is enabled
    for username in sorted(instance_map.keys()):
        running_instances = instance_map[username]
        identity = _get_identity_from_tenant_name(provider, username)
        if identity and running_instances:
            try:
                driver = get_cached_driver(identity=identity)
                core_running_instances = [
                    convert_esh_instance(driver, inst,
                        identity.provider.uuid, identity.uuid,
                        identity.created_by) for inst in running_instances]
            except Exception as exc:
                logger.exception("Could not convert running instances for %s" % username)
                continue
        else:
            #No running instances.
            core_running_instances = []
        #Using the 'known' list of running instances, cleanup the DB
        core_instances = _cleanup_missing_instances(identity, core_running_instances)
        allocation_result = user_over_allocation_enforcement(
                provider, username,
                print_logs, start_date, end_date)
    if print_logs:
        logger.removeHandler(consolehandler)


@task(name="monitor_sizes")
def monitor_sizes():
    """
    Update sizes for each active provider.
    """
    for p in Provider.get_active():
        monitor_sizes_for.apply_async(args=[p.id])


@task(name="monitor_sizes_for")
def monitor_sizes_for(provider_id, print_logs=False):
    """
    Run the set of tasks related to monitoring sizes for a provider.
    Optionally, provide a list of usernames to monitor
    While debugging, print_logs=True can be very helpful.
    start_date and end_date allow you to search a 'non-standard' window of time.
    """
    from service.driver import get_admin_driver

    if print_logs:
        import logging
        import sys
        consolehandler = logging.StreamHandler(sys.stdout)
        consolehandler.setLevel(logging.DEBUG)
        logger.addHandler(consolehandler)

    provider = Provider.objects.get(id=provider_id)
    admin_driver = get_admin_driver(provider)
    # Non-End dated sizes on this provider
    db_sizes = Size.objects.filter(only_current(), provider=provider)
    all_sizes = admin_driver.list_sizes()
    seen_sizes = []
    for cloud_size in all_sizes:
        core_size = convert_esh_size(cloud_size, provider.uuid)
        seen_sizes.append(core_size)

    now_time = timezone.now()
    needs_end_date = [size for size in db_sizes if size not in seen_sizes]
    for size in needs_end_date:
        logger.debug("End dating inactive size: %s" % size)
        size.end_date = now_time
        size.save()

    if print_logs:
        logger.removeHandler(consolehandler)
