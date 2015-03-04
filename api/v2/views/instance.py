from rest_framework import viewsets
from core.models import Instance
from ..serializers import InstanceSerializer
from core.query import only_current


class InstanceViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows providers to be viewed or edited.
    """
    queryset = Instance.objects.all()
    serializer_class = InstanceSerializer
    filter_fields = ('created_by__id', 'projects')

    def get_queryset(self):
        """
        Filter projects by current user
        """
        user = self.request.user
        return Instance.objects.filter(only_current(), created_by=user)
