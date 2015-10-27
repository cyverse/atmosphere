from core.models import Instance
from api.v2.serializers.details import InstanceSerializer
from core.query import only_current

from api.v1.views.instance import Instance as V1Instance

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

    def list(self, request, *args, **kwargs):
        import ipdb;ipdb.set_trace()
        return super(InstanceViewSet, self).list(request, *args, **kwargs)

    def get_queryset(self):
        """
        Filter projects by current user.
        """
        user = self.request.user
        qs = Instance.objects.filter(created_by=user)
        if 'archived' in self.request.query_params:
            return qs
        # Return current results
        return qs.filter(only_current())

    def perform_destroy(self, instance):
        return V1Instance().delete(self.request,
                                   instance.provider_alias,
                                   instance.created_by_identity.uuid,
                                   instance.id)
