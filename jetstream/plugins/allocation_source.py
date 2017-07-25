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

__all__ = ['JetstreamAllocationSourcePlugin']