from django.utils import timezone
from rest_framework import permissions

from core.models import ResourceRequest, StatusType
from core import email
from api.v2.serializers.details import (
    ResourceRequestSerializer, AdminResourceRequestSerializer
)
from api.v2.views.base import AuthModelViewSet, AdminModelViewSet
from api.v2.views.mixins import MultipleFieldLookup


class AdminResourceRequestViewSet(MultipleFieldLookup, AdminModelViewSet):

    """
    API endpoint that allows admins to view/update user requests
    """
    lookup_fields = ("id", "uuid")
    queryset = ResourceRequest.objects.none()
    model = ResourceRequest
    serializer_class = AdminResourceRequestSerializer
    filter_fields = ('status__id', 'status__name', 'created_by__username')

    def get_queryset(self):
        """
        Return users requests or all the requests if the user is an admin.
        """
        return \
            self.model.objects.all() \
            .select_related("created_by", "status") \
            .order_by('-start_date')

    def close_action(self, instance):
        """
        Add an end date to a request and take no further action
        """
        instance.end_date = timezone.now()
        instance.save()

    def approve_action(self, instance):
        """
        Notify the user, the request was approved
        """
        email.send_approved_resource_email(
            user=instance.created_by,
            request=instance.request,
            reason=instance.admin_message)

    def deny_action(self, instance):
        """
        Notify the user that the request was denied
        """
        instance.end_date = timezone.now()
        instance.save()
        email.send_denied_resource_email(
            user=instance.created_by,
            request=instance.request,
            reason=instance.admin_message)

    def perform_update(self, serializer):
        """
        Updates the request and performs any update actions.
        """
        serializer.save()
        instance = serializer.instance

        status_name = instance.status.name
        if status_name == "approved":
            self.approve_action(instance)
        elif status_name == "denied":
            self.deny_action(instance)
        elif status_name == "closed":
            self.close_action(instance)

    def perform_destroy(self, instance):
        """
        Add an end date to a request and take no further action
        """
        status, _ = StatusType.objects.get_or_create(name="closed")
        instance.status = status
        instance.end_date = timezone.now()
        instance.save()


class UserUpdatePermission(permissions.BasePermission):
    message = 'A user can update the status to closed but cannot update the admin message'

    def has_permission(self, request, view):
        if request.method not in ['PATCH', 'PUT']:
            return True

        # No permission to update admin_message
        if 'admin_message' in request.data:
            return False

        # No permission to approve/deny, only close
        try:
            request_status_pk = request.data['status']['id']
        except KeyError:
            return True
        closing_status, _ = StatusType.objects.get_or_create(name='closed')
        return request_status_pk == closing_status.pk


class ResourceRequestViewSet(MultipleFieldLookup, AuthModelViewSet):
    """
    API endpoint that allows users to view or close their requests
    """
    lookup_fields = ("id", "uuid")
    permission_classes = AuthModelViewSet.permission_classes + (UserUpdatePermission,)
    queryset = ResourceRequest.objects.none()
    model = ResourceRequest
    serializer_class = ResourceRequestSerializer
    filter_fields = ('status__id', 'status__name')

    def get_queryset(self):
        """
        Return requests created by requesting user
        """
        return \
            self.model.objects.filter(created_by=self.request.user) \
            .select_related("created_by", "status") \
            .order_by('-start_date')

    def perform_create(self, serializer):
        """
        Create a resource request
        """
        status, _ = StatusType.objects.get_or_create(name='pending')
        serializer.save(
            created_by=self.request.user,
            status=status
        )
        options = {}
        if serializer.initial_data.get("admin_url"):
            options={"admin_url": serializer.initial_data.get("admin_url") + str(instance.id)}
        email.resource_request_email(self.request,
                                     self.request.user.username,
                                     instance.request,
                                     instance.description,
                                     options)

    def perform_destroy(self, serializer):
        """
        Close a resource request
        """
        status, _ = StatusType.objects.get_or_create(name="closed")
        serializer.save(status=status, end_date=timezone.now())
