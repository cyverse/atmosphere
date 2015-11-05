from core.models.status_type import StatusType

from api.v2.serializers.details import StatusTypeSerializer
from api.v2.views.base import AuthReadOnlyViewSet
from api.v2.views.mixins import MultipleFieldLookup


class StatusTypeViewSet(MultipleFieldLookup, AuthReadOnlyViewSet):

    """
    API endpoint that allows status types to be viewed.
    """
    lookup_fields = ("id", "uuid")
    queryset = StatusType.objects.all()
    serializer_class = StatusTypeSerializer
