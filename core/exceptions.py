"""
exceptions - Core exceptions
"""


class InvalidMembership(Exception):
    """
    The membership provided is not valid
    """


class SourceNotFound(Exception):
    """
    InstanceSource doesn't have an associated source.
    """


class ProviderLimitExceeded(Exception):
    """
    A limit was exceeded for the specific provider
    """
