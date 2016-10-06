"""
Atmosphere API's extension of DRF permissions.
"""

from django.contrib.auth.models import AnonymousUser
from rest_framework import permissions

from threepio import logger

from core.models.cloud_admin import CloudAdministrator, cloud_admin_list, get_cloud_admin_for_provider
from core.models import Group, MaintenanceRecord, AtmosphereUser, Project

from api import ServiceUnavailable
from api.v2.serializers.details import (
    ProjectSerializer, VolumeSerializer,
    InstanceSerializer, ExternalLinkSerializer,
    ProjectInstanceSerializer, ProjectVolumeSerializer,
    ProjectExternalLinkSerializer, ProjectApplicationSerializer
)

class ImageOwnerUpdateAllowed(permissions.BasePermission):

    def has_permission(self, request, view):
        user = request.user
        if request.METHOD != 'PATCH':
            return True
        image_id = view.kwargs.get('image_id')
        if not image_id:
            logger.warn("Could not find kwarg:'image_id'")
            return False
        if user.is_superuser() or \
                user.is_staff() or \
                any(app for app in
                    user.application_set.filter(id=image_id)):
            return True
        return False


class ProjectOwnerRequired(permissions.BasePermission):
    message = "You must be the project owner to execute this command."

    def has_permission(self, request, view):
        auth_user = request.user
        provider_uuid = view.kwargs.get('provider_uuid')
        identity_uuid = view.kwargs.get('identity_uuid')
        instance_id = view.kwargs.get('instance_id')
        volume_id = view.kwargs.get('volume_id')
        key = view.kwargs.get('pk')
        request_method = request._request.META['REQUEST_METHOD']
        request_path = request._request.path
        SerializerCls = getattr(view, 'serializer_class', None)
        # The V2 APIs don't use 'named kwargs' so everything comes in as 'pk'
        # To overcome this hurdle and disambiguate views, we use the fact that every viewset defines a serializer class.
        if SerializerCls == VolumeSerializer:
            volume_id = key
        elif SerializerCls == InstanceSerializer:
            instance_id = key

        if instance_id or SerializerCls == InstanceSerializer:
            # Permissions specific to /v1/views/instance.py, /v2/views/volume.py
            if request_method == 'GET':
                # Allow 'GET' list/details requests for the v1 APIs
                return True
            return self.test_instance_permissions(auth_user, instance_id)
        elif volume_id or SerializerCls == VolumeSerializer:
            # Permissions specific to /v1/views/volume.py, /v2/views/volume.py
            if request_method == 'GET':
                # Allow 'GET' list/details requests for the v1 APIs
                return True
            return self.test_volume_permissions(auth_user, volume_id)
        elif SerializerCls == ProjectSerializer:
            if not key and request_method == 'GET':
                return True  # Querying for the list -- Allow it.
            # Permissions specific to /v2/views/project.py
            return self.test_project_permissions(auth_user, key)
        elif SerializerCls == ExternalLinkSerializer:
            if not key and request_method == 'GET':
                return True  # Querying for the list -- Allow it.
            # Permissions specific to /v2/views/link.py
            return self.test_link_permissions(auth_user, key)
        elif SerializerCls in [
                ProjectApplicationSerializer, ProjectExternalLinkSerializer,
                ProjectInstanceSerializer, ProjectVolumeSerializer]:
            if request_method == 'GET':
                # Allow 'GET' requests for the v1 APIs
                return True
            # Permissions specific to /v2/views/link.py
            return self.test_project_resource_permissions(
                SerializerCls.Meta.model, auth_user, key)
        elif identity_uuid:
            # Permissions specific to v1 Instance and Volume Creation
            return self.test_identity_permissions(auth_user, identity_uuid)
        else:
            logger.warn("Could not find kwarg:'instance_id' or 'volume_id'")
            return False

    def test_identity_permissions(self, auth_user, identity_id):
        identity = auth_user.shared_identities(can_edit=True).filter(
            uuid=identity_id).first()
        return identity

    def test_link_permissions(self, auth_user, link_id):
        link = auth_user.shared_links(can_edit=True).filter(
            pk=link_id).first()
        return link

    def test_project_resource_permissions(self, ModelCls, auth_user, project_id):
        from core.query import (
            is_project_member, project_member_can_edit
        )
        query = is_project_member(auth_user)
        query &= project_member_can_edit(auth_user)

        proj = ModelCls.objects.filter(
            query).filter(pk=project_id).first()
        return proj

    def test_project_permissions(self, auth_user, project_id):
        proj = auth_user.shared_projects(can_edit=True).filter(
            pk=project_id).first()
        return proj

    def test_volume_permissions(self, auth_user, volume_id):
        volume = auth_user.shared_volumes(can_edit=True).filter(
            instance_source__identifier=volume_id).first()
        return volume

    def test_instance_permissions(self, auth_user, instance_id):
        instance = auth_user.shared_instances(can_edit=True).filter(
            provider_alias=instance_id).first()
        return instance


class ProjectMemberRequired(ProjectOwnerRequired):
    def test_link_permissions(self, auth_user, link_id):
        link = auth_user.shared_links(can_edit=False).filter(
            pk=link_id).first()
        return link

    def test_project_resource_permissions(self, ModelCls, auth_user, project_id):
        from core.query import (
            is_project_member, project_member_can_edit
        )
        query = is_project_member(auth_user)

        proj = ModelCls.objects.filter(
            query).filter(pk=project_id).first()
        return proj

    def test_project_permissions(self, auth_user, project_id):
        proj = auth_user.shared_projects().filter(
            pk=project_id).first()
        return proj

    def test_volume_permissions(self, auth_user, volume_id):
        volume = auth_user.shared_volumes().filter(
            provider_alias=volume_id).first()
        return volume

    def test_instance_permissions(self, auth_user, instance_id):
        instance = auth_user.shared_instances().filter(
            provider_alias=instance_id).first()
        return instance


class ApiAuthRequired(permissions.BasePermission):
    message = "The requested user could not be authenticated."

    def has_permission(self, request, view):
        return request.user.is_authenticated()


class EnabledUserRequired(permissions.BasePermission):
    message = "The account you are using has been disabled. "\
        "Please contact your Cloud Administrator for more information."

    def has_permission(self, request, view):
        if isinstance(request.user, AnonymousUser):
            return False
        return request.user.is_enabled


def _get_administrator_account(user, admin_uuid):
    try:
        return cloud_admin_list(user).get(uuid=admin_uuid)
    except CloudAdministrator.DoesNotExist:
        return None


class CloudAdminRequired(permissions.BasePermission):

    def has_permission(self, request, view):
        if not request.user.is_authenticated():
            return False

        kwargs = request.parser_context.get('kwargs', {})
        admin_uuid = kwargs.get('cloud_admin_uuid')
        # Generally you would use this keyword to look at a
        # SPECIFIC cloud_admin
        if admin_uuid:
            admin = _get_administrator_account(
                request.user, admin_uuid)
        else:
            admin = cloud_admin_list(request.user).exists()
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
        # You would use this keyword to update a
        # SPECIFIC cloud_admin
        if admin_uuid:
            admin = _get_administrator_account(
                request.user, admin_uuid)
        # When a 'specific Provider' is involved,
        # Ensure that the request.user has admin permission
        # before updating on that provider.
        elif provider_uuid:
            admin = get_cloud_admin_for_provider(
                request.user, provider_uuid)
        # In the event 'cloud_admin' or 'provider' is not specified
        # This decorator will ensure that the request user
        # holds 'CloudAdmin' privileges on at least one provider
        # in order to make the action.
        else:
            admin = cloud_admin_list(request.user).exists()

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
            staff_username = request.session.get('username','')
            staff_user = AtmosphereUser.objects.filter(username=staff_username).first()
            if staff_user and staff_user.is_staff:
                return True
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
        # Allow Application/Image owners to make changes
        if obj.created_by == request.user:
            return True

        # FIXME: move queries into a model manager
        user_groups = Group.objects.filter(user=request.user)
        app_groups = Group.objects.filter(applications=obj)
        return (user_groups & app_groups).exists()
