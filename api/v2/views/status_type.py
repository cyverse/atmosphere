from core.models.status_type import StatusType

from api.v2.serializers.details import StatusTypeSerializer
from api.v2.base import AuthReadOnlyViewSet


class StatusTypeViewSet(AuthReadOnlyViewSet):
    """
    API endpoint that allows status types to be viewed.
    """
    queryset = StatusType.objects.all()
    serializer_class = StatusTypeSerializer
