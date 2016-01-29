from core.models import ResourceRequest
from core import email

from django.utils import timezone

from api.v2.serializers.details import ResourceRequestSerializer,\
    UserResourceRequestSerializer
from api.v2.views.base import BaseRequestViewSet
from core import tasks
from service.tasks import admin as admin_task


class ResourceRequestViewSet(BaseRequestViewSet):

    """
    API endpoint that allows resource request to be viewed or edited.
    """
    queryset = ResourceRequest.objects.none()
    model = ResourceRequest
    serializer_class = UserResourceRequestSerializer
    admin_serializer_class = ResourceRequestSerializer
    filter_fields = ('status__id', 'status__name', 'created_by__username')

    def close_action(self, instance):
        """
        Add an end date to a request and take no further action
        """
        self.end_date = timezone.now()
        self.save()

    def submit_action(self, instance):
        """
        Submits a resource request email
        """
        requested_resource = instance.request
        reason_for_request = instance.description
        username = self.request.user.username
        email.resource_request_email(self.request, username,
                                     requested_resource,
                                     reason_for_request)

    def approve_action(self, instance):
        """
        Updates the resource for the request
        """
        self.end_date = timezone.now()
        self.save()
        membership = instance.membership
        membership.quota = instance.quota or membership.quota
        membership.allocation = instance.allocation or membership.allocation
        membership.save()
        identity = membership.identity

        email_task = email.send_approved_resource_email(
            user=instance.created_by,
            request=instance.request,
            reason=instance.admin_message)

        admin_task.set_provider_quota.apply_async(
            args=[str(identity.uuid)],
            link=[tasks.close_request.si(instance), email_task],
            link_error=tasks.set_request_as_failed.si(instance))

    def deny_action(self, instance):
        """
        Notify the user that the request was denied
        """
        self.end_date = timezone.now()
        self.save()
        email.send_denied_resource_email(
            user=instance.created_by,
            request=instance.request,
            reason=instance.admin_message)
