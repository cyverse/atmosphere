from datetime import datetime

from django.utils import timezone

from core.models.instance import Instance


def filter_by_time_delta(instances, delta):
    min_time = timezone.now() - delta
    return [i for i in instances if not i.end_date or i.end_date > min_time]

def get_time(user, delta):
    total_time = 0
    if typeof(user) is str:
        user = User.objects.filter(username=user)
    instances = filter_by_time_delta(Instance.objects.filter(created_by=user))
    for i in instances:
        pass
    return total_time
