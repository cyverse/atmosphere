import sys

from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from core.models import AtmosphereUser as User

from core.models import IdentityMembership, Identity
from core.models.instance import Instance, convert_esh_instance
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
    keys = map( lambda x: x[1], list(formatter.parse(fmt)))
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

def get_burn_time(user, identity_id, delta, threshold):
    """
    INPUT: Total time allowed, total time used (so far),
    The CPU cores multiplier
    """
    #DONT MOVE -- Circ.Dep.
    from service.instance import get_core_instances
    if type(user) is not User:
        user = User.objects.filter(username=user)
    if type(delta) is not timedelta:
        delta = timedelta(minutes=delta)
    if type(threshold) is not timedelta:
        delta = timedelta(minutes=threshold)
    time_used = core_instance_time(user, identity_id, delta)
    time_remaining = threshold - time_used
    #If we used all of our allocation, dont calculate burn time
    if time_remaining < timedelta(0):
        return None
    instances = get_core_instances(identity_id)
    #If we have no instances, burn-time does not apply
    if not instances:
        return None
    cpu_cores = sum([inst.esh.size.cpu for inst in instances
                     if inst.last_history()
                     and inst.last_history().is_active()])
    #If we have no active cores, burn-time does not apply
    if cpu_cores == 0:
        return None
    #Calculate burn time by dividing remaining time over running cores
    burn_time = time_remaining/cpu_cores
    return burn_time


def current_instance_time(user, instances, identity_id, delta_time):
    """
    Add all running instances to core, so that the database is up to date
    before calling 'core_instance_time'
    """
    from api import get_esh_driver
    ident = Identity.objects.get(id=identity_id)
    driver = get_esh_driver(ident)
    core_instance_list = [
            convert_esh_instance(driver, inst,
                                 ident.provider.id, ident.id, user)
                          for inst in instances]
    #All instances that don't have an end-date should be
    #included, even if all of their time is not.
    time_used = core_instance_time(user, ident.id, delta_time, running=core_instance_list)
    return time_used



def core_instance_time(user, identity_id, delta, running=[]):
    """
    Called 'core_instance' time because it relies on the data
    in core to be relevant. 
    
    If you (potentially) have new instances on the
    driver, you should be using current_instance_time
    """
    if type(user) is not User:
        user = User.objects.filter(username=user)[0]
    if type(delta) is not timedelta:
        delta = timedelta(minutes=delta)
    total_time = timedelta(0)
    past_time = timezone.now() - delta
    #Calculate only the specific users time allocation..
    instances = Instance.objects.filter(
            Q(end_date=None) | Q(end_date__gt=past_time),
            created_by=user, created_by_identity__id=identity_id)
    logger.debug('Calculating time of %s instances' % len(instances))
    logger.debug(
            'INSTANCE,username,alias[:5],start_date,end_date,run_time,total_time')
    logger.debug(
            'HISTORY,username,alias[:5],status,size_name,size_cpu,'
            'start_count,end_count, active_time,cpu_time')
    for idx, i in enumerate(instances):
        #If we know what instances are running, and this isn't one of them,
        # it missed end-dating. Lets do something about it
        if running and i not in running:
            i.end_date_all()
        run_time = i.get_active_time(delta)
        new_total = run_time + total_time
        logger.debug(
                'INSTANCE,%s,%s,%s,%s,%s,%s'
                % (user.username, i.provider_alias[:5],
                   strfdate(i.start_date),
                   strfdate(i.end_date),
                   strfdelta(run_time),
                   strfdelta(new_total)))
        total_time = new_total
    logger.debug("TOTAL,%s,%s"
            % (user.username, strfdelta(total_time)))
    return total_time



def delta_to_minutes(tdelta):
    total_seconds = tdelta.days*86400 + tdelta.seconds
    total_mins = total_seconds / 60
    return total_mins


def delta_to_hours(tdelta):
    total_mins = delta_to_minutes(tdelta)
    hours = total_mins / 60
    return hours


def get_allocation(username, identity_id):
    membership = IdentityMembership.objects.filter(identity__id=identity_id,
                                                member__name=username)
    if not membership:
        return None
    return membership[0].allocation


def get_delta(allocation, time_period):
    # Monthly Time Allocation
    if time_period and time_period.months == 1:
        now = timezone.now()
        if time_period.day <= now.day:
            allocation_time = timezone.datetime(year=now.year,
                                                month=now.month,
                                                day=time_period.day,
                                                tzinfo=timezone.utc)
        else:
            prev = now - time_period
            allocation_time = timezone.datetime(year=prev.year,
                                                month=prev.month,
                                                day=time_period.day,
                                                tzinfo=timezone.utc)
        return now - allocation_time
    else:
        return timedelta(minutes=allocation.delta)


def check_over_allocation(username, identity_id,
                          time_period=None):
    """
    Check if an identity is over allocation.

    If time_period is timedelta(month=1) then delta_time is from the
    beginning of the month to now otherwise delta_time is allocation.delta.
    Get all instance histories created between now and delta_time. Check
    that cumulative time of instances do not exceed threshold.

    True if allocation has been exceeded, otherwise False.
    """
    allocation = get_allocation(username, identity_id)
    if not allocation:
        return (False, timedelta(0))
    delta_time = get_delta(allocation, time_period)
    max_time_allowed = timedelta(minutes=allocation.threshold)
    logger.debug("%s Allocation: %s Time allowed"
                 % (username, max_time_allowed))
    total_time_used = core_instance_time(username, identity_id, delta_time)
    logger.debug("%s Time Used: %s"
                 % (username, total_time_used))
    time_diff = max_time_allowed - total_time_used
    if time_diff.total_seconds() <= 0:
        logger.debug("%s is OVER their allowed quota by %s" %
                     (username, time_diff))
        return (True, time_diff)
    return (False, time_diff)
