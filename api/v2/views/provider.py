from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import detail_route
from core.models import Provider, Group
from api.v2.serializers.details import ProviderSerializer
from api.v2.serializers.summaries import SizeSummarySerializer
from core.query import only_current_provider


class ProviderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows providers to be viewed or edited.
    """
    queryset = Provider.objects.all()
    serializer_class = ProviderSerializer
    permission_classes = (IsAuthenticated,)
    http_method_names = ['get', 'head', 'options', 'trace']

    def get_permissions(self):
        method = self.request.method
        if method == 'DELETE' or method == 'PUT':
            self.permission_classes = (IsAdminUser,)

        return super(viewsets.GenericViewSet, self).get_permissions()

    def get_queryset(self):
        """
        Filter projects by current user
        """
        user = self.request.user
        group = Group.objects.get(name=user.username)
        provider_ids = group.identities.filter(only_current_provider(), provider__active=True).values_list('provider', flat=True)
        return Provider.objects.filter(id__in=provider_ids)

    @detail_route()
    def sizes(self, *args, **kwargs):
        provider = self.get_object()
        self.get_queryset = super(viewsets.ModelViewSet, self).get_queryset
        self.queryset = provider.size_set.get_queryset()
        self.serializer_class = SizeSummarySerializer
        return self.list(self, *args, **kwargs)
