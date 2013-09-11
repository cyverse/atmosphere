"""
Atmosphere API's extension of DRF permissions.
"""
from rest_framework.permissions import BasePermission


class InMaintenance(BasePermission):
    def has_permission(self, request, view):
        return True
