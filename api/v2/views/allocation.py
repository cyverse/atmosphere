from rest_framework import viewsets
from core.models import Allocation
from api.v2.serializers.details import AllocationSerializer


class AllocationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows providers to be viewed or edited.
    """
    queryset = Allocation.objects.all()
    serializer_class = AllocationSerializer
    http_method_names = ['get', 'head', 'options', 'trace']
