from django.db.models import Q
from django.utils import timezone


def only_active_provider(now_time=None):
    """
    Use this query on any model with a 'provider.end_date'
    to limit the objects to those
    that have not past their end_date
    """
    if not now_time:
        now_time = timezone.now()
    return Q(provider__active=True)


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
        return (
                Q(providermachine__instance_source__provider__end_date__isnull=True) | \
                Q(providermachine__instance_source__provider__end_date__gt=now_time)) & \
            Q(providermachine__instance_source__provider__active=True)

    def _in_range():
        return (Q(providermachine__instance_source__end_date__isnull=True) | \
                Q(providermachine__instance_source__end_date__gt=now_time)) &\
            Q(providermachine__instance_source__start_date__lt=now_time)

    if not now_time:
        now_time = timezone.now()
    return _in_range() & _active_provider()


def only_current_apps(now_time=None):
    def _active_provider():
        return (Q(versions__machines__instance_source__provider__end_date__isnull=True) | \
                Q(versions__machines__instance_source__provider__end_date__gt=now_time)) & \
            Q(versions__machines__instance_source__provider__active=True)

    def _in_range():
        """
        Return all applications that:
        * have NO end date OR
        * whose end date has not yet occurred
        AND
        * whose start date is in the past.
        """
        return (Q(end_date__isnull=True) | \
                Q(end_date__gt=now_time)) & \
            Q(start_date__lt=now_time)
    def _versions_in_range():
        """
        Return all applications that:
        * have versions with NO end date OR
        * have versions whose end date has not yet occurred
        AND
        * have versions whose start date is in the past.
        """
        return (Q(versions__end_date__isnull=True) | \
                Q(versions__end_date__gt=now_time)) & \
            Q(versions__start_date__lt=now_time)
    def _machines_in_range():
        """
        Return all applications that:
        * have machines with NO end date OR
        * have machines whose end date has not yet occurred
        AND
        * have machines whose start date is in the past.
        """
        return (Q(versions__machines__instance_source__end_date__isnull=True) | \
                Q(versions__machines__instance_source__end_date__gt=now_time)) & \
            Q(versions__machines__instance_source__start_date__lt=now_time)
    def _active_machines():
        """
        This method should eliminate any application such-that:
        * ALL machines (in all versions) of the app are end dated OR
        * ALL machines (in all versions) of the app have an inactive provider
        """
        pass
    def _active_versions():
        """
        This method should eliminate any application such-that:
        * ALL versions of this application have been end dated.
        """
        pass
    if not now_time:
        now_time = timezone.now()
    return _in_range() & _versions_in_range() & _machines_in_range() & _active_provider()


def only_current_machines_in_version(now_time=None):
    def _active_provider():
        return (Q(machines__instance_source__provider__end_date__isnull=True) | \
                Q(machines__instance_source__provider__end_date__gt=now_time)) &\
                    Q(machines__instance_source__provider__active=True)
    def _in_range():
        return (Q(machines__instance_source__end_date__isnull=True) | \
         Q(machines__instance_source__end_date__gt=now_time)) & \
            Q(machines__instance_source__start_date__lt=now_time)
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

def source_in_range(now_time=None):
    """
    Filters current instance_sources ignoring provider.
    """
    def _in_range():
        return (Q(instance_source__end_date__isnull=True) |
                Q(instance_source__end_date__gt=now_time)) &\
            Q(instance_source__start_date__lt=now_time)
    if not now_time:
        now_time = timezone.now()
    return _in_range()

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


def _query_membership_for_user(user):
    """
    All *Memberhsips use 'group' as the keyname, this will check
    that the memberships returned are only those that the user is in.
    """
    if not user:
        return None
    return Q(group__id__in=user.group_set.values('id'))
