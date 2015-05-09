from core.models import Allocation

from api.v2.serializers.details import AllocationSerializer
from api.v2.views.base import AuthReadOnlyViewSet


class AllocationViewSet(AuthReadOnlyViewSet):
    """
    API endpoint that allows providers to be viewed or edited.
    """

    queryset = Allocation.objects.all()
    serializer_class = AllocationSerializer
    http_method_names = ['get', 'head', 'options', 'trace']
