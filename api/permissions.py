"""
Atmosphere API's extension of DRF permissions.
"""
from rest_framework import permissions


#NOTE: It would be better to use Object-level permissions here.
class ProjectOwnerRequired(permissions.BasePermission):
    def has_permission(self, request, view):
        auth_user = request.user
        project_id = view.kwargs.get('project_id')
        if not project_id:
            logger.warn("Could not find kwarg:'project_id'")
            return False
        return any(
                group for group in auth_user.group_set.all()
                if group.projects.filter(id=project_id))

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
