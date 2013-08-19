from datetime import datetime, timedelta

from django.utils import timezone
from django.contrib.auth.models import User

from core.models.instance import Instance


def filter_by_time_delta(instances, delta):
    min_time = timezone.now() - delta
    return [i for i in instances if not i.end_date or i.end_date > min_time]

def get_instance_time(instance):
    status_history = instance.instancestatushistory_set.all()
    if not status_history:
        # No status history, use entire length of instance
        return timezone.now() - instance.start_date
    active_time = timedelta(0)
    for inst_state in status_history:
        if not inst_state.status == 'active':
            continue
        if inst_state.end_date:
            active_time += inst_state.end_date - inst_state.start_date
        else:
            active_time += timezone.now() - inst_state.start_date
    return active_time

def get_time(user, delta):
    total_time = timedelta(0)
    if type(user) is str:
        user = User.objects.filter(username=user)
    instances = filter_by_time_delta(Instance.objects.filter(created_by=user),
                                     delta)
    for i in instances:
        total_time += get_instance_time(i)
    return total_time

def get_allocation(username, identity_id):
    membership = IdentityMembership.objects.get(identity__id=identity_id,
                                                member__name=username)
    return membership.allocation

def check_allocation(username, identity_id):
    """
    Get identity-specific allocation
    Grab all instances created between now and 'delta'
    Check that cumulative time of instances do not exceed threshold
    TRUE = Okay to launch
    """
    allocation = get_allocation(username, identity_id)
    if not allocation:
        #No allocation, not over quota
        return True
    delta_time = timedelta(minutes=allocation.delta)
    total_time_used = get_time(username, delta_time)
    max_time_allowed = timedelta(minutes=allocation.threshold)
    if total_time_used >= max_time_allowed:
        logger.info("%s is over their allowed quota by %s minutes" % (username, 
    return total_time_used < max_time_allowed

