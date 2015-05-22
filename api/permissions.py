"""
Atmosphere API's extension of DRF permissions.
"""

from django.contrib.auth.models import AnonymousUser

from rest_framework import permissions

from threepio import logger

from core.models.cloud_admin import CloudAdministrator
from core.models import Group, MaintenanceRecord

from api import ServiceUnavailable


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
        return request.user.is_authenticated()


def _get_administrator_accounts(user):
    try:
        return CloudAdministrator.objects.filter(user=user)
    except CloudAdministrator.DoesNotExist:
        return CloudAdministrator.objects.none()


def _get_administrator_account_for(user, provider_uuid):
    try:
        return _get_administrator_accounts(user)\
            .get(provider__uuid=provider_uuid)
    except CloudAdministrator.DoesNotExist:
        return None


def _get_administrator_account(user, admin_uuid):
    try:
        return _get_administrator_accounts(user).get(uuid=admin_uuid)
    except CloudAdministrator.DoesNotExist:
        return None


class CloudAdminRequired(permissions.BasePermission):

    def has_permission(self, request, view):
        if not request.user.is_authenticated():
            return False

        kwargs = request.parser_context.get('kwargs', {})
        admin_uuid = kwargs.get('cloud_admin_uuid')
        if admin_uuid:
            admin = _get_administrator_account(
                request.user, admin_uuid)
        else:
            admin = _get_administrator_accounts(request.user).exists()
        return admin or request.user.is_staff


class CloudAdminUpdatingRequired(permissions.BasePermission):

    def has_permission(self, request, view):
        user = request.user
        if request.method in permissions.SAFE_METHODS:
            return user.is_authenticated()
        # UPDATE requires a cloud administrator account
        kwargs = request.parser_context.get('kwargs', {})
        admin_uuid = kwargs.get('cloud_admin_uuid')
        provider_uuid = kwargs.get('provider_uuid')
        if admin_uuid:
            admin = _get_administrator_account(
                request.user, admin_uuid)
        elif provider_uuid:
            admin = _get_administrator_account_for(
                request.user, provider_uuid)
        else:
            admin = _get_administrator_accounts(request.user).exists()

        return True if admin else False


class IsAdminOrReadOnly(permissions.BasePermission):

    """
    The request is authenticated as an admin, or is a read-only request.
    """

    def has_permission(self, request, view):
        return (
            request.method in permissions.SAFE_METHODS or
            request.user and request.user.is_staff
        )


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


def get_maintenance_messages(records):
    """
    Combine maintenance messages together into a string.
    """
    messages = ""
    for r in records:
        if messages:
            messages += " | "
        messages += "%s: %s" % (r.title, r.message)
    return messages


class InMaintenance(permissions.BasePermission):

    """
    Return a 503 Service unavailable if in maintenance.

    Exceptions: for DjangoUser staff.
    """

    def has_permission(self, request, view):
        records = MaintenanceRecord.active()\
                                   .filter(provider__isnull=True)
        if records:
            if not request.user.is_staff:
                raise ServiceUnavailable(
                    detail=get_maintenance_messages(records))
        return True


class CanEditOrReadOnly(permissions.BasePermission):
    """
    Authorize the request if the user is the creator or the request is a
    safe operation.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user.is_staff:
            return True
        return hasattr(obj, "created_by") and obj.created_by == request.user


class ApplicationMemberOrReadOnly(permissions.BasePermission):
    """
    Authorize the request if the user is member of the application or
    the request is a safe operation.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user.is_staff:
            return True

        #FIXME: move queries into a model manager
        user_groups = Group.objects.filter(user=request.user)
        app_groups = Group.objects.filter(applications=obj)
        return (user_groups & app_groups).exists()
