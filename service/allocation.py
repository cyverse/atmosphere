from datetime import timedelta

from django.utils import timezone
from core.models import AtmosphereUser as User

from core.models import IdentityMembership, Identity
from core.models.instance import Instance
from threepio import logger


def filter_by_time_delta(instances, delta):
    """
    Return all running instances AND all instances between now and 'delta'
    """
    time_ago = timezone.now() - delta
    running_insts = [i for i in instances if not i.end_date]
    older_insts = [i for i in instances if i.end_date
                   and i.end_date > time_ago]
    older_insts.extend(running_insts)
    return older_insts


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
    time_used = get_time(user, identity_id, delta)
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


def get_time(user, identity_id, delta):
    if type(user) is not User:
        user = User.objects.filter(username=user)
    if type(delta) is not timedelta:
        delta = timedelta(minutes=delta)

    total_time = timedelta(0)
    #Calculate only the specific users time allocation..
    instances = Instance.objects.filter(created_by=user,
                                        created_by_identity__id=identity_id)
    instances = filter_by_time_delta(instances, delta)
    #logger.debug('Calculating time of %s instances' % len(instances))
    for idx, i in enumerate(instances):
        #Runtime cannot be larger than the total 'window' of time observed
        run_time = min(i.get_active_time(), delta)
        new_total = run_time + total_time
        #logger.debug(
        #        '%s:<Instance %s> %s + %s = %s'
        #        % (idx, i.provider_alias[-5:],
        #           delta_to_minutes(run_time),
        #           delta_to_minutes(total_time)
        #           delta_to_minutes(new_total)))
        total_time = new_total
    #logger.debug("%s hours == %s minutes == %s"
    #        % (delta_to_hours(total_time),
    #           delta_to_minutes(total_time),
    #            total_time))
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
    total_time_used = get_time(username, identity_id, delta_time)
    time_diff = max_time_allowed - total_time_used
    if time_diff.total_seconds() <= 0:
        logger.debug("%s is over their allowed quota by %s" %
                     (username, time_diff))
        return (True, time_diff)
    return (False, time_diff)
