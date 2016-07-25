"""
Jetstream exceptions
"""


class TASAPIException(Exception):
    """
    This exception is raised when something has changed with TAS API
    that results in the failure of a TASAllocationReport
    """
    pass

class TASPluginException(Exception):
    """
    This exception is raised when something has changed with the Jetstream
    'plugin to the Auth model' (Atmosphere)
    """
    pass
