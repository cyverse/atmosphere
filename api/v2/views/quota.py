from core.models import Quota

from api.v2.serializers.details import QuotaSerializer
from api.v2.views.base import AuthViewSet
from api.v2.views.mixins import MultipleFieldLookup


class QuotaViewSet(MultipleFieldLookup, AuthViewSet):

    """
    API endpoint that allows providers to be viewed or edited.
    """
    lookup_fields = ("id","uuid")
    queryset = Quota.objects.all()
    serializer_class = QuotaSerializer
    http_method_names = ['get', 'head', 'options', 'trace']
