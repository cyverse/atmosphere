"""
Atmosphere API's extension of DRF permissions.
"""
from rest_framework import permissions

from threepio import logger


# NOTE: It would be better to use Object-level permissions here.
class ProjectOwnerRequired(permissions.BasePermission):
    def has_permission(self, request, view):
        auth_user = request.user
        project_uuid = view.kwargs.get('project_uuid')
        if not project_uuid:
            logger.warn("Could not find kwarg:'project_uuid'")
            return False
        return any(
            group for group in auth_user.group_set.all()
            if group.projects.filter(uuid=project_uuid))


class ApiAuthRequired(permissions.BasePermission):
    def has_permission(self, request, view):
        auth_user = request.user.is_authenticated()
        return auth_user


class CloudAdminRequired(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user

        if not user.is_authenticated():
            return False

        return user.is_staff or user.is_superuser


class ApiAuthIgnore(permissions.BasePermission):
    def has_permission(self, request, view):
        return True


class ApiAuthOptional(permissions.BasePermission):
    def has_permission(self, request, view):
        # Allow access to GET/OPTIONS/HEAD operations.
        if request.method in permissions.SAFE_METHODS:
            return True
        # ASSERT: User trying to POST/PUT/PATCH, must be authenticated
        return request.user.is_authenticated()


class InMaintenance(permissions.BasePermission):
    def has_permission(self, request, view):
        return True
