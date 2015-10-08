"""
exceptions - Core exceptions
"""


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
