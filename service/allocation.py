from datetime import datetime, timedelta

from django.utils import timezone
from django.contrib.auth.models import User

from core.models import IdentityMembership
from core.models.instance import Instance

from threepio import logger


def filter_by_time_delta(instances, delta):
    """
    Return all running instances AND all instances between now and 'delta'
    """
    min_time = timezone.now() - delta
    return [i for i in instances if not i.end_date or i.end_date > min_time]


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
    logger.debug('Calculating time of %s instances' % len(instances))
    for i in instances:
        run_time = min(i.get_active_time(), delta)
        logger.debug('Instance %s running for %s' %
                    (i.provider_alias, run_time))
        total_time += run_time
    return total_time


def get_allocation(username, identity_id):
    membership = IdentityMembership.objects.get(identity__id=identity_id,
                                                member__name=username)
    return membership.allocation


def check_over_allocation(username, identity_id):
    """
    Get identity-specific allocation
    Grab all instances created between now and 'delta'
    Check that cumulative time of instances do not exceed threshold

    False if there is no allocation OR okay to launch.
    True if time allocation is exceeded
    """
    allocation = get_allocation(username, identity_id)
    if not allocation:
        #No allocation, so you fail.
        return (False, timedelta(0))
    delta_time = timedelta(minutes=allocation.delta)
    max_time_allowed = timedelta(minutes=allocation.threshold)
    total_time_used = get_time(username, identity_id, delta_time,
                               max_time_allowed)
    time_diff = max_time_allowed - total_time_used
    if time_diff.total_seconds() <= 0:
        logger.debug("%s is over their allowed quota by %s" %
                     (username, time_diff))
        return (True, time_diff)
    return (False, time_diff)
