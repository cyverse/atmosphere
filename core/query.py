from django.db.models import Q
from django.utils import timezone

def only_active():
    """
    Use this query on any model with 'end_date'
    to limit the objects to those
    that have not past their end_date
    """
    return Q(end_date=None) | Q(end_date__gt=timezone.now())

