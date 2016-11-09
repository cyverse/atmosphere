from django.db.models import Q
from django.utils import timezone


def inactive_versions():
    return (
        # Contains at least one version without an end-date OR
        (Q(num_versions__gt=0) & Q(versions__end_date__isnull=True)) |
        # conatins at least one machine without an end-date
        (
            Q(num_machines__gt=0) &
            Q(versions__machines__instance_source__end_date__isnull=True)
        )
    )


def only_active_provider():
    """
    Use this query on any model with a 'provider.active'
    to limit the objects to those
    that have an active provider
    """
    return Q(provider__active=True)


def only_current_tokens(now_time=None):
    """
    Filters out inactive tokens.
    """
    if not now_time:
        now_time = timezone.now()
    return (Q(expireTime__isnull=True) |
            Q(expireTime__gt=now_time)) &\
        Q(issuedTime__lt=now_time)


def only_current_provider(now_time=None):
    """
    Use this query on core.Identity:
    Filters 'current' providers by removing those
    who have exceeded their end-date.
    """
    if not now_time:
        now_time = timezone.now()
    return (Q(provider__end_date__isnull=True) |
            Q(provider__end_date__gt=now_time)) &\
        Q(provider__active=True) &\
        Q(provider__start_date__lt=now_time)


def only_current_instances(now_time=None):
    """
    Filter the current instances.
    """
    def _active_source():
        """
        An instance.source is active if the provider is active and un-end-dated.
        """
        return (Q(source__provider__end_date__isnull=True) |
                Q(source__provider__end_date__gt=now_time)) &\
            Q(source__provider__active=True)

    def _source_in_range():
        """
        A source is in range if it has been started before -now-
        AND if it has not been end-dated before -now-
        """
        return (Q(source__end_date__isnull=True) |
                Q(source__end_date__gt=now_time)) &\
            Q(source__start_date__lt=now_time)

    if not now_time:
        now_time = timezone.now()
    #NOTE: Purposefully absent: 'source_in_range'
    return only_current() & _active_source()



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


def only_public_providers(now_time=None):
    return (Q(instance_source__provider__public=True))


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


def only_active_provider_memberships(user=None, now_time=None):
    if not now_time:
        now_time = timezone.now()
    query = (
        Q(identity__provider__end_date__isnull=True) |
        Q(identity__provider__end_date__gt=now_time)
        ) & Q(identity__provider__active=True)
    if user:
        query = query & Q(member__user__username=user.username)
    return query


def only_active_memberships(user=None, now_time=None):
    if not now_time:
        now_time = timezone.now()
    query = (
        Q(identity__provider__end_date__isnull=True) |
        Q(identity__provider__end_date__gt=now_time)
        ) & (
        Q(end_date__isnull=True) |
        Q(end_date__gt=now_time)
        ) & Q(identity__provider__active=True)
    if user:
        query = query & Q(member__user__username=user.username)
    return query


def user_provider_machine_set(user):
    """
    A query specifically for 'ProviderMachine'
    Will return the provider machines created by 'user'
    """
    query = (Q(instance_source__provider_id__in=user.provider_ids()) |
             Q(application_version__application__created_by=user) |
             Q(instance_source__created_by=user))
    return query


def in_provider_list(provider_list, key_override=None):
    """
    All ProviderMachines who have a matching provider in this list..
    """
    if not key_override:
        key_override = "instance_source__provider"
    if not key_override.endswith("__in"):
        key_override += "__in"
    return Q(**{key_override: provider_list})


def _query_membership_for_user(user):
    """
    All *Memberhsips use 'group' as the keyname, this will check
    that the memberships returned are only those that the user is in.
    """
    if not user:
        return None
    return Q(group__id__in=user.group_set.values('id'))

def images_shared_with_user(user):
    """
    Images with versions or machines belonging to the user's groups
    """
    group_ids = user.group_ids()
    return (Q(versions__machines__members__id__in=group_ids) |
        Q(versions__membership__id__in=group_ids))

def created_by_user(user):
    """
    Images created by a username
    """
    return Q(created_by__username__exact=user.username)

def in_users_providers(user):
    """
    Images on providers that the user belongs to
    """
    return Q(versions__machines__instance_source__provider__in=user.current_providers)

def contains_credential(key, value):
    """
    Use this query to determine if `Identity` contains credential key/value
    """
    return (Q(credential__key=key) &
        Q(credential__value=value))

def provider_credential(key, value):
    """
    Use this query to determine if `Provider` contains credential key/value
    """
    return (Q(providercredential__key=key) &
        Q(providercredential__value=value))
