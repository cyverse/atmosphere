from rest_framework import viewsets
from core.models import ProviderType
from ..serializers import ProviderTypeSerializer


class ProviderTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows instance actions to be viewed or edited.
    """
    queryset = ProviderType.objects.all()
    serializer_class = ProviderTypeSerializer
    http_method_names = ['get', 'head', 'options', 'trace']
