from core.models import Instance
from api.v2.serializers.details import InstanceSerializer
from core.query import only_current

from api.v2.serializers.details import InstanceSerializer
from api.v2.views.base import AuthViewSet


class InstanceViewSet(AuthViewSet):
    """
    API endpoint that allows providers to be viewed or edited.
    """

    queryset = Instance.objects.all()
    serializer_class = InstanceSerializer
    filter_fields = ('created_by__id', 'projects')
    http_method_names = ['get', 'put', 'patch', 'head', 'options', 'trace']

    def get_queryset(self):
        """
        Filter projects by current user.
        """
        user = self.request.user
        return Instance.objects.filter(only_current(), created_by=user)
