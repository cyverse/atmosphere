from django.db.models import Q
from django.utils import timezone


def only_current_provider(now_time=None):
    """
    Use this query on any model with a 'provider.end_date'
    to limit the objects to those
    that have not past their end_date
    """
    if not now_time:
        now_time = timezone.now()
    return Q(provider__end_date=None) | Q(provider__end_date__gt=now_time)

def only_current(now_time=None):
    """
    Use this query on any model with 'end_date'
    to limit the objects to those
    that have not past their end_date
    """
    if not now_time:
        now_time = timezone.now()
    return Q(end_date=None) | Q(end_date__gt=now_time)
