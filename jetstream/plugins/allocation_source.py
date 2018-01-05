from django.conf import settings

from core.models import AllocationSource


class JetstreamAllocationSourcePlugin(object):
    def ensure_user_allocation_source(self, user, provider=None):
        """Ensures that a user has valid allocation sources.

        Will check the TAS API and mirror what it finds in the AllocationSource & UserAllocationSource tables locally.

        :param user: The user to check
        :type user: core.models.AtmosphereUser
        :param provider: A provider (not used by JetstreamAllocationSourcePlugin)
        :type provider: core.models.Provider
        :return: Whether the user has valid allocation sources
        :rtype: bool
        """
        return True  # TODO: Implement this

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


__all__ = ['JetstreamAllocationSourcePlugin']
