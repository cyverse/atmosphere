from core.models import Identity

from api.v2.views.base import AdminModelViewSet
from api.v2.serializers.details.resource_request_actions import (
    ResourceRequest_UpdateQuotaSerializer)


class ResourceRequest_UpdateQuotaViewSet(AdminModelViewSet):
    """
    Use this API endpoint to POST a new action:
    - Set 'quota' to identity
    - require traceability data: resource_request_id, approved_by_username
    """
    http_method_names = ['post','options','trace']
    serializer_class = ResourceRequest_UpdateQuotaSerializer

    class Meta:
        #FIXME: When we find a better way to "Use viewsets without models", replace this one too.
        #NOTE: Ignore the line below; remove when FIXME above is addressed.
        model = Identity
