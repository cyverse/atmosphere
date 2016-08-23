"""
exceptions - Core exceptions
"""


class InvalidUser(Exception):
    """
    The user provided is not valid
    """
    pass


class InvalidMembership(Exception):
    """
    The membership provided is not valid
    """
    pass


class SourceNotFound(Exception):
    """
    InstanceSource doesn't have an associated source.
    """
    pass


class RequestLimitExceeded(Exception):
    """
    A limit was exceeded for the specific request
    """
    pass


class ProviderLimitExceeded(Exception):

    """
    A limit was exceeded for the specific provider
    """
    pass


class ProviderNotActive(Exception):
    """
    The provider that was requested is not active
    """
    def __init__(self, provider, *args, **kwargs):
        self.message = "Cannot create driver on an inactive provider: %s" \
                       % (provider.location,)
    pass
