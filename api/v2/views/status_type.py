from rest_framework import viewsets
from core.models.status_type import StatusType
from api.v2.serializers.details import StatusTypeSerializer


class StatusTypeViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows status types to be viewed.
    """
    queryset = StatusType.objects.all()
    serializer_class = StatusTypeSerializer
