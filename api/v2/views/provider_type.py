from core.models import ProviderType

from api.v2.serializers.details import ProviderTypeSerializer
from api.v2.views.base import AuthViewSet
from api.v2.views.mixins import MultipleFieldLookup


class ProviderTypeViewSet(AuthViewSet):

    """
    API endpoint that allows instance actions to be viewed or edited.
    """
    queryset = ProviderType.objects.all()
    serializer_class = ProviderTypeSerializer
    http_method_names = ['get', 'head', 'options', 'trace']
