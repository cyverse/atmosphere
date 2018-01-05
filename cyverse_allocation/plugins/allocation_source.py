import uuid

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from threepio import logger

from core.models import EventTable, AllocationSource, AtmosphereUser, UserAllocationSource


class FlexibleAllocationSourcePlugin(object):
    def ensure_user_allocation_source(self, user, provider=None):
        """Ensures that a user has valid allocation sources.

        Will create a new one and/or assign an existing one to the user

        :param user: The user to check
        :type user: core.models.AtmosphereUser
        :param provider: A provider (not used by FlexibleAllocationSourcePlugin)
        :type provider: core.models.Provider
        :return: Whether the user has valid allocation sources
        :rtype: bool
        """

        return _ensure_user_allocation_source(user)

    def get_enforcement_override(self, user, allocation_source, provider=None):
        """Returns whether (and how) to override the enforcement for a particular user, allocation source and provider
        combination.

        :param user: The user to check (not used by this plugin)
        :type user: core.models.AtmosphereUser
        :param allocation_source: The allocation source to check
        :type allocation_source: core.models.AllocationSource
        :param provider: The provider (not used by this plugin)
        :type provider: core.models.Provider
        :return: The enforcement override behaviour for the allocation source on the provider
        :rtype: core.plugins.EnforcementOverrideChoice
        """
        return _get_enforcement_override(allocation_source)


def _get_enforcement_override(allocation_source):
    """Returns whether (and how) to override the enforcement for an allocation source.

        :param allocation_source: The allocation source to check
        :type allocation_source: core.models.AllocationSource
        :return: The enforcement override behaviour for the allocation source on the provider
        :rtype: core.plugins.EnforcementOverrideChoice
        """
    assert isinstance(allocation_source, AllocationSource)
    import core.plugins
    if allocation_source.name in getattr(settings, 'ALLOCATION_OVERRIDES_NEVER_ENFORCE', []):
        return core.plugins.EnforcementOverrideChoice.NEVER_ENFORCE
    if allocation_source.name in getattr(settings, 'ALLOCATION_OVERRIDES_ALWAYS_ENFORCE', []):
        return core.plugins.EnforcementOverrideChoice.ALWAYS_ENFORCE
    return core.plugins.EnforcementOverrideChoice.NO_OVERRIDE


def _ensure_user_allocation_source(user):
    """Ensures that a user has valid allocation sources.

    Will create a new one and/or assign an existing one to the user

    :param user: The user to check
    :type user: core.models.AtmosphereUser
    :return: Whether the user has valid allocation sources
    :rtype: bool
    """

    # Safety valve: Don't try to create an AllocationSource and UserAllocationSource if the AtmosphereUser does
    # not exist. You *will* get into an inconsistent state if this happens - the AllocationSource and the
    # `user_allocation_source_created` event will exist, but with no matching UserAllocationSource
    assert isinstance(user, AtmosphereUser)
    allocation_source_name = user.username

    try:
        allocation_source = AllocationSource.objects.get(name=allocation_source_name)
    except ObjectDoesNotExist:
        logger.debug('No AllocationSource with name %s found. Creating a new AllocationSource.',
                     allocation_source_name)
        _create_allocation_source(allocation_source_name)
        allocation_source = AllocationSource.objects.get(name=allocation_source_name)
    else:
        logger.debug('AllocationSource with name %s exists. Skipping creation step.', allocation_source_name)
    try:
        user_allocation_source = UserAllocationSource.objects.get(user=user,
                                                                  allocation_source=allocation_source)
    except ObjectDoesNotExist:
        logger.debug('No UserAllocationSource with name %s found. Assigning allocation source to user.',
                     allocation_source_name)
        _assign_user_allocation_source(allocation_source, user)
    else:
        logger.debug('UserAllocationSource with name %s exists: %s Skipping creation step.',
                     allocation_source_name, user_allocation_source)
    return True


def _create_allocation_source(name):
    default_compute_allowed = getattr(settings, 'ALLOCATION_SOURCE_COMPUTE_ALLOWED', 168)
    payload = {
        'uuid': str(uuid.uuid4()),
        'allocation_source_name': name,
        'compute_allowed': default_compute_allowed,  # TODO: Make this a plugin configurable
        'renewal_strategy': 'default'
    }
    event = EventTable(
        name='allocation_source_created_or_renewed',
        entity_id=name,
        payload=payload
    )
    event.save()


def _assign_user_allocation_source(source_to_assign, user_to_assign):
    assert isinstance(source_to_assign, AllocationSource)
    assert isinstance(user_to_assign, AtmosphereUser)
    username_to_assign = user_to_assign.username
    payload = {'allocation_source_name': source_to_assign.name}
    event = EventTable(
        name='user_allocation_source_created',
        entity_id=username_to_assign,
        payload=payload
    )
    event.save()


__all__ = ['FlexibleAllocationSourcePlugin']
