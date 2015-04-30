from core.models import PlatformType

from api.v2.serializers.details import PlatformTypeSerializer
from api.v2.base import AuthViewSet


class PlatformTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows instance actions to be viewed or edited.
    """

    queryset = PlatformType.objects.all()
    serializer_class = PlatformTypeSerializer
    http_method_names = ['get', 'head', 'options', 'trace']
