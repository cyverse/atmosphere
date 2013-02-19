"""
Atmosphere core exceptions.

"""

class ServiceException(Exception):
    pass

class MissingArgsException(ServiceException):
    pass
