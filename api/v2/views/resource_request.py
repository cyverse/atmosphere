from core.models import ResourceRequest
from core import email

from django.utils import timezone

from api.v2.serializers.details import ResourceRequestSerializer,\
    UserResourceRequestSerializer
from api.v2.views.base import BaseRequestViewSet
from api.pagination import OptionalPagination
from core import tasks


class ResourceRequestViewSet(BaseRequestViewSet):

    """
    API endpoint that allows resource request to be viewed or edited.
    """
    queryset = ResourceRequest.objects.none()
    model = ResourceRequest
    serializer_class = UserResourceRequestSerializer
    pagination_class = OptionalPagination
    admin_serializer_class = ResourceRequestSerializer
    filter_fields = ('status__id', 'status__name', 'created_by__username')

    def close_action(self, instance):
        """
        Add an end date to a request and take no further action
        """
        instance.end_date = timezone.now()
        instance.save()

    def submit_action(self, instance, options={}):
        """
        Submits a resource request email
        """
        requested_resource = instance.request
        reason_for_request = instance.description
        username = self.request.user.username
        email.resource_request_email(self.request, username,
                                     requested_resource,
                                     reason_for_request,
                                     options)

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
            reason=instance.admin_message).delay()
