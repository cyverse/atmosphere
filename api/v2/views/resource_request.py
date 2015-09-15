from core.models import ResourceRequest
from core.email import send_denied_resource_email, resource_request_email

from api.v2.serializers.details import ResourceRequestSerializer,\
    UserResourceRequestSerializer
from api.v2.views.base import BaseRequestViewSet


class ResourceRequestViewSet(BaseRequestViewSet):

    """
    API endpoint that allows resource request to be viewed or edited.
    """
    queryset = ResourceRequest.objects.none()
    model = ResourceRequest
    serializer_class = UserResourceRequestSerializer
    admin_serializer_class = ResourceRequestSerializer
    filter_fields = ('status__id', 'status__name')

    def submit_action(self, instance):
        """
        Submits a resource request email
        """
        requested_resource = instance.request
        reason_for_request = instance.description
        username = self.request.user.username
        resource_request_email(self.request, username, requested_resource,
                               reason_for_request)

    def approve_action(self, instance):
        """
        Updates the resource for the request
        """
        membership = instance.membership
        membership.quota = instance.quota
        membership.allocation = instance.allocation
        membership.approve_quota(instance.id)
        membership.save()

    def deny_action(self, instance):
        """
        Notify the user that the request was denied
        """
        send_denied_resource_email(user=instance.created_by,
                                   request=instance.request,
                                   reason=instance.admin_message)
