from core.models import Quota

from api.v2.serializers.details import QuotaSerializer
from api.v2.views.base import AuthViewSet
from api.v2.views.mixins import MultipleFieldLookup
from api.permissions import CanEditOrReadOnly


class QuotaViewSet(MultipleFieldLookup, AuthViewSet):

    """
    API endpoint that allows providers to be viewed or edited.
    NOTE: we have *INTENTIONALLY* left out the ability to *UPDATE* or *DELETE* a quota.
    This can have *disasterous cascade issues* on other fields. DONT DELETE or UPDATE quota!
    """
    lookup_fields = ("id", "uuid")
    queryset = Quota.objects.all()
    serializer_class = QuotaSerializer
    permission_classes = (
        CanEditOrReadOnly,
    )
    http_method_names = ['get', 'post', 'head', 'options', 'trace']
