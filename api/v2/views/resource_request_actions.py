from rest_framework.response import Response
from rest_framework import status

from api.v2.views.base import AdminViewSet
from api.v2.serializers.details.resource_request_actions import (
    ResourceRequest_UpdateQuotaSerializer)


class ResourceRequest_UpdateQuotaViewSet(AdminViewSet):
    """
    Use this API endpoint to POST a new action:
    - Set 'quota' to identity
    - require traceability data: resource_request_id, approved_by_username
    """
    http_method_names = ['post', 'options', 'trace']

    def create(self, request):
        serializer = ResourceRequest_UpdateQuotaSerializer(
                data=request.data,
                context={'request': self.request})
        serializer.is_valid(raise_exception=True)
        try:
            serializer.save()
        except Exception as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
