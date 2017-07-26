"""
Jetstream exceptions
"""


class TASAPIException(Exception):
    """
    This is a general exception when communicating with TAS API
    """
    pass


class NoTaccUserForXsedeException(TASAPIException):
    """
    This exception is raised when TAS API can't find a TACC user account for an XSEDE username
    """
    pass


class NoAccountForUsernameException(TASAPIException):
    """
    This exception is raised when we try to get projects or allocations for a TACC username which does not map to a
    TACC account
    """
    pass

class TASPluginException(Exception):
    """
    This exception is raised when something has changed with the Jetstream
    'plugin to the Auth model' (Atmosphere)
    """
    pass
