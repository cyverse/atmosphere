"""
authentication exception methods.
"""
from rest_framework.exceptions import PermissionDenied


class Unauthorized(PermissionDenied):

    """
    This class is used when the user is carrying valid authentication,
    but the user is not authorized to make the request.
    """
