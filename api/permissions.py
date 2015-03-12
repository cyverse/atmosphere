"""
Atmosphere API's extension of DRF permissions.
"""
from core.models.cloud_admin import CloudAdministrator

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


def _get_administrator_accounts(user):
    try:
        return CloudAdministrator.objects.filter(user=user)
    except CloudAdministrator.DoesNotExist:
        return CloudAdministrator.objects.none()


def _get_administrator_account(user, admin_uuid):
    try:
        return _get_administrator_accounts(user).get(uuid=admin_uuid)
    except CloudAdministrator.DoesNotExist:
        return None


class CloudAdminRequired(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated():
            return False

        kwargs = request.parser_context.get('kwargs', {})
        admin_uuid = kwargs.get('cloud_admin_uuid')
        if admin_uuid:
            admin = _get_administrator_account(
                request.user, admin_uuid)
        else:
            admin = _get_administrator_accounts(request.user).exists()

        return True if admin else False


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
