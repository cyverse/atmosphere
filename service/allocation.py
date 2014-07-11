import sys

from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from core.models import AtmosphereUser as User

from core.models import IdentityMembership, Identity
from core.models.instance import Instance, convert_esh_instance
from threepio import logger


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
    total_time_used, _ = core_instance_time(username, identity_id, delta_time)
    logger.debug("%s Time Used: %s"
                 % (username, total_time_used))
    time_diff = max_time_allowed - total_time_used
    if time_diff.total_seconds() <= 0:
        logger.debug("%s is OVER their allowed quota by %s" %
                     (username, time_diff))
        return (True, time_diff)
    return (False, time_diff)


def get_allocation(username, identity_id):
    membership = IdentityMembership.objects.get(identity__id=identity_id,
                                                member__name=username)
    return membership.allocation


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


def get_burn_time(user, identity_id, delta, threshold, now_time=None):
    """
    INPUT: Total time allowed, total time used (so far),
    OUTPUT: delta representing time remaining (from now)
    """
    #DONT MOVE -- Circ.Dep.
    from service.instance import get_core_instances
    #Allow for multiple 'types' to be sent in
    if type(user) is not User:
        #not user, so this is a str with username
        user = User.objects.filter(username=user)
    if type(delta) is not timedelta:
        #not delta, so this is the int for minutes
        delta = timedelta(minutes=delta)
    if type(threshold) is not timedelta:
        #not delta, so this is the int for minutes
        delta = timedelta(minutes=threshold)

    #Assume we are burned out.
    burn_time = timedelta(0)

    #If we have no instances, burn-time does not apply
    instances = get_core_instances(identity_id)
    if not instances:
        return burn_time

    #Remaining time: What your allotted - What you used before now
    time_used, _ = core_instance_time(
            user, identity_id, delta,
            now_time=now_time)
    #delta = delta - delta
    time_remaining = threshold - time_used

    #If we used all of our allocation, we are burned out.
    if time_remaining < timedelta(0):
        return burn_time

    cpu_cores = get_cpu_count(user, identity_id)
    #If we have no active cores, burn-time does not apply
    if cpu_cores == 0:
        return burn_time
    #Calculate burn time by dividing remaining time over running cores
    #delta / int = delta (ex. 300 mins / 3 = 100 mins)
    burn_time = time_remaining/cpu_cores
    return burn_time


def get_cpu_count(user, identity_id):
    #Counting only running instances:
    instances = Instance.objects.filter(
            end_date=None, created_by=user,
            created_by_identity__id=identity_id)
    #Looking at only the last history
    cpu_total = 0
    for inst in instances:
        last_history = inst.get_last_history()
        if last_history and last_history.is_active():
            cpu_total += last_history.size.cpu
    return cpu_total


def current_instance_time(user, instances, identity_id, delta_time):
    """
    Converts all running instances to core, 
    so that the database is up to date before calling 'core_instance_time'
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



def core_instance_time(user, identity_id, delta, running=[], now_time=None):
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
    if not now_time:
        now_time = timezone.now() 
    past_time = now_time - delta

    #Calculate only the specific users time allocation..
    instances = Instance.objects.filter(
            Q(end_date=None) | Q(end_date__gt=past_time),
            created_by=user, created_by_identity__id=identity_id)
    instance_status_map = {}
    for idx, i in enumerate(instances):
        #If we know what instances are running, and this isn't one of them,
        # it missed end-dating. Lets do something about it
        if running and i not in running:
            i.end_date_all()
        active_time, status_list = i.get_active_time(past_time, now_time)
        instance_status_map[i] = status_list
        new_total = active_time + total_time
        total_time = new_total
    return total_time, instance_status_map

def delta_to_minutes(tdelta):
    total_seconds = tdelta.days*86400 + tdelta.seconds
    total_mins = total_seconds / 60
    return total_mins


def delta_to_hours(tdelta):
    total_mins = delta_to_minutes(tdelta)
    hours = total_mins / 60
    return hours
