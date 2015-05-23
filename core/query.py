from django.db.models import Q
from django.utils import timezone


def only_current_provider(now_time=None):
    """
    Filters the current active providers.
    """
    if not now_time:
        now_time = timezone.now()
    return (Q(provider__end_date__isnull=True) |
            Q(provider__end_date__gt=now_time)) &\
        Q(provider__active=True) &\
        Q(provider__start_date__lt=now_time)


def only_current_machines(now_time=None):
    """
    Filters the current provider_machines.
    """
    def _active_provider():
        return \
            (Q(providermachine__instance_source__provider__end_date__isnull=True) |
             Q(providermachine__instance_source__provider__end_date__gt=now_time)) &\
            Q(providermachine__instance_source__provider__active=True)

    def _in_range():
        return (Q(providermachine__instance_source__end_date__isnull=True) |
                Q(providermachine__instance_source__end_date__gt=now_time)) &\
            Q(providermachine__instance_source__start_date__lt=now_time)

    if not now_time:
        now_time = timezone.now()
    return _in_range() & _active_provider()


def only_current_source(now_time=None):
    """
    Filters the current instance_sources.
    """
    def _active_provider():
        return (Q(instance_source__provider__end_date__isnull=True) |
                Q(instance_source__provider__end_date__gt=now_time)) &\
            Q(instance_source__provider__active=True)

    def _in_range():
        return (Q(instance_source__end_date__isnull=True) |
                Q(instance_source__end_date__gt=now_time)) &\
            Q(instance_source__start_date__lt=now_time)

    if not now_time:
        now_time = timezone.now()
    return _in_range() & _active_provider()


def only_current(now_time=None):
    """
    Filters in range using start_date and end_date.
    """
    if not now_time:
        now_time = timezone.now()
    return (Q(end_date=None) | Q(end_date__gt=now_time)) &\
        Q(start_date__lt=now_time)


def _active_identity_membership(user, now_time=None):
    from core.models import IdentityMembership
    if not now_time:
        now_time = timezone.now()
    return IdentityMembership.objects.filter(
        Q(identity__provider__end_date__isnull=True) |
        Q(identity__provider__end_date__gt=now_time),
        identity__provider__active=True,
        member__user__username=user.username)
