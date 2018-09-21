"""
 Instance metrics stored in graphite
"""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from api import permissions
from api.v2.exceptions import failure_response

from core.models import Instance
from core.metrics.instance import get_instance_metrics
from threepio import logger


class MetricViewSet(GenericViewSet):

    permission_classes = (
        permissions.InMaintenance, permissions.ApiAuthRequired
    )

    queryset = Instance.objects.all()

    lookup_field = 'provider_alias'

    def get_queryset(self):
        if self.request.user.is_superuser:
            return self.queryset
        return Instance.objects.filter(created_by=self.request.user)

    def get_key(self, instance, params):
        inputs = [instance.provider_alias] + params.values()
        return ":".join(map(str, inputs))

    def retrieve(self, *args, **kwargs):
        instance = self.get_object()
        params = self.request.query_params
        try:
            instance_metrics = get_instance_metrics(instance, params)
        except Exception as exc:
            logger.exception("Failed to retrieve instance metrics")
            return failure_response(status.HTTP_409_CONFLICT, str(exc.message))
        return Response(instance_metrics)
