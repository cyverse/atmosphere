from core.models import Allocation

from api.v2.serializers.details import AllocationSerializer
from api.v2.views.base import AuthViewSet
from api.v2.views.mixins import MultipleFieldLookup
from api.permissions import CanEditOrReadOnly
class AllocationViewSet(MultipleFieldLookup, AuthViewSet):

    """
    API endpoint that allows providers to be viewed or edited.
    NOTE: we have *INTENTIONALLY* left out the ability to *UPDATE* or *DELETE* a allocation.
    This can have *disasterous cascade issues* on other fields. DONT DELETE or UPDATE allocation!
    """
    lookup_fields = ("id", "uuid")
    queryset = Allocation.objects.all()
    serializer_class = AllocationSerializer
    permission_classes = (
        CanEditOrReadOnly,
    )
    http_method_names = ['get', 'post', 'head', 'options', 'trace']
