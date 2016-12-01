"""
Atmosphere API's extension of DRF permissions.
"""

from django.contrib.auth.models import AnonymousUser
from rest_framework import permissions

from threepio import logger

from core.models.cloud_admin import CloudAdministrator, cloud_admin_list, get_cloud_admin_for_provider
from core.models import Group, MaintenanceRecord, AtmosphereUser, ExternalLink, Volume, Instance, Project

from api import ServiceUnavailable
from django.conf import settings


class ImageOwnerUpdateAllowed(permissions.BasePermission):

    def has_permission(self, request, view):
        user = request.user
        if request.METHOD != 'PATCH':
            return True
        image_id = view.kwargs.get('image_id')
        if not image_id:
            logger.warn("Could not find kwarg:'image_id'")
            return False
        if user.is_superuser or \
                user.is_staff or \
                any(app for app in
                    user.application_set.filter(id=image_id)):
            return True
        return False


class ProjectOwnerRequired(permissions.BasePermission):

    def has_permission(self, request, view):
        auth_user = request.user
        project_uuid = view.kwargs.get('project_uuid')
        if not project_uuid:
            logger.warn("Could not find kwarg:'project_uuid'")
            return False
        return any(
            membership.group for membership in auth_user.memberships.all()
            if membership.group.projects.filter(uuid=project_uuid))


class ProjectLeaderRequired(permissions.BasePermission):
    message = "The requested user is not a leader of the project."

    def has_permission(self, request, view):
        """ TODO: Finish later"""
        auth_user = request.user
        if not auth_user.is_authenticated():
            return False
        request_path = request._request.path
        if request_path.startswith("/api/v1"):
            return self.v1_leadership_test(request, view)
        return self.v2_leadership_test(request, view)

    def test_project_permissions(user, project_id):
        project_kwargs = {}
        if type(project_id) == int:
            project_kwargs = {'id': project_id}
        else:
            project_kwargs = {'uuid': project_id}
        return Project.shared_with_user(user, is_leader=True).filter(**project_kwargs).exists()

    def test_link_permissions(user, link_id):
        link_kwargs = {}
        if type(link_id) == int:
            link_kwargs = {'id': link_id}
        else:
            link_kwargs = {'uuid': link_id}
        return ExternalLink.shared_with_user(user, is_leader=True).filter(**link_kwargs).exists()

    def test_volume_permissions(self, user, volume_id):
        volume_kwargs = {}
        if type(volume_id) == int:
            volume_kwargs = {'id': volume_id}
        else:
            volume_kwargs = {'instance_source__identifier': volume_id}
        return Volume.shared_with_user(user, is_leader=True).filter(**volume_kwargs).exists()

    def test_instance_permissions(self, user, instance_id):
        instance_kwargs = {}
        if type(instance_id) == int:
            instance_kwargs = {'id': instance_id}
        else:
            instance_kwargs = {'provider_alias': instance_id}
        return Instance.shared_with_user(user, is_leader=True).filter(**instance_kwargs).exists()

    def v1_leadership_test(self, request, view):
        auth_user = request.user
        identity_uuid = view.kwargs.get('identity_uuid')
        instance_id = view.kwargs.get('instance_id')
        volume_id = view.kwargs.get('volume_id')
        request_method = request._request.META['REQUEST_METHOD']
        if request_method == 'GET':
            return True
        if instance_id:
            return self.test_instance_permissions(auth_user, instance_id)
        if volume_id:
            return self.test_volume_permissions(auth_user, volume_id)
        elif identity_uuid:
            # Permissions specific to v1 Instance and Volume Creation
            return self.test_identity_permissions(auth_user, identity_uuid)
        else:
            logger.warn("Could not find kwarg:'instance_id' or 'volume_id'")
            return False

    def v2_leadership_test(self, request, view):
        auth_user = request.user
        key = view.kwargs.get('pk')
        request_method = request._request.META['REQUEST_METHOD']
        if request_method == 'GET':
            return True  # Querying for the list -- Allow it.

        SerializerCls = getattr(view, 'serializer_class', None)
        serializer_classname = SerializerCls.__name__
        # The V2 APIs don't use 'named kwargs' so everything comes in as 'pk'
        # To overcome this hurdle and disambiguate views, we use the fact that every viewset defines a serializer class.
        if serializer_classname == "VolumeSerializer":
            volume_id = key
            return self.test_volume_permissions(auth_user, volume_id)
        elif serializer_classname == "InstanceSerializer":
            instance_id = key
            return self.test_instance_permissions(auth_user, instance_id)
        #TODO: Re-evaluate logic below this line.
        elif serializer_classname == "ProjectSerializer":
            # Permissions specific to /v2/views/project.py
            return self.test_project_permissions(auth_user, key)
        elif serializer_classname == "ExternalLinkSerializer":
            # Permissions specific to /v2/views/link.py
            return self.test_link_permissions(auth_user, key)
        elif serializer_classname in [
                "ProjectApplicationSerializer", "ProjectExternalLinkSerializer",
                "ProjectInstanceSerializer", "ProjectVolumeSerializer"]:
            # Permissions specific to /v2/views/link.py
            return self.test_project_resource_permissions(
                SerializerCls.Meta.model, auth_user, key)
        else:
            return True


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
            session_username = request.session.get('username','')
            request_username = request.user.username
            #TODO: Optional logic related to session_username -- the one who is 'Authenticated'..
            atmo_user = AtmosphereUser.objects.filter(username=request_username).first()
            if atmo_user and request_username in settings.MAINTENANCE_EXEMPT_USERNAMES:
                return True
            else:
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
