from core.models import Allocation

from api.v2.serializers.details import AllocationSerializer
from api.v2.views.base import AuthViewSet
from api.v2.views.mixins import MultipleFieldLookup

class AllocationViewSet(MultipleFieldLookup, AuthViewSet):

    """
    API endpoint that allows providers to be viewed or edited.
    """
    lookup_fields = ("id", "uuid")
    queryset = Allocation.objects.all()
    serializer_class = AllocationSerializer
    http_method_names = ['get', 'head', 'options', 'trace']
