"""
Atmosphere API's extension of DRF permissions.
"""
from rest_framework import permissions

class ApiAuthRequired(permissions.BasePermission):
    def has_permission(self, request, view):
        auth_user = request.user.is_authenticated()
        return auth_user

class ApiAuthOptional(permissions.BasePermission):
    def has_permission(self, request, view):
        #Allow access to GET/OPTIONS/HEAD operations.
        if request.method in permissions.SAFE_METHODS:
            return True
        #ASSERT: User trying to POST/PUT/PATCH, must be authenticated
        return request.user.is_authenticated()

class InMaintenance(permissions.BasePermission):
    def has_permission(self, request, view):
        return True
