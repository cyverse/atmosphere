from core.models import QuotaRequest
from core.email import send_denied_quota_email

from web.emails import quota_request_email

from api.v2.views.base import BaseRequestViewSet
from api.v2.serializers.details import QuotaRequestSerializer,\
    UserQuotaRequestSerializer


class QuotaRequestViewSet(BaseRequestViewSet):
    """
    API endpoint that allows quota request to be viewed or edited.
    """
    queryset = QuotaRequest.objects.none()
    model = QuotaRequest
    serializer_class = UserQuotaRequestSerializer
    admin_serializer_class = QuotaRequestSerializer
    filter_fields = ('status__id', 'status__name')

    def submit_action(self, instance):
        """
        Submits a quota request email
        """
        requested_quota = instance.request
        reason_for_request = instance.description
        username = self.request.user.username
        quota_request_email(self.request, username, requested_quota,
                            reason_for_request)

    def approve_action(self, instance):
        """
        Updates the quota for the request
        """
        membership = instance.membership
        membership.quota = instance.quota
        membership.approve_quota(instance.uuid)

    def deny_action(self, instance):
        """
        Notify the user that the request was denied
        """
        send_denied_quota_email(user=instance.created_by,
                                request=instance.request,
                                reason=instance.admin_message)
