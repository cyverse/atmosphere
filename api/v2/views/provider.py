from django.contrib.auth.models import AnonymousUser
from rest_framework.decorators import detail_route
from rest_framework import viewsets

from core.models import Provider, Group
from core.query import only_current_provider, only_current

from api.v2.serializers.details import ProviderSerializer
from api.v2.serializers.post import ProviderSerializer as POST_ProviderSerializer
from api.v2.serializers.summaries import SizeSummarySerializer
from api.v2.views.base import AuthOptionalViewSet
from api.v2.views.mixins import MultipleFieldLookup


class ProviderViewSet(MultipleFieldLookup, AuthOptionalViewSet):
    """
    API endpoint that allows providers to be viewed or edited.
    """
    lookup_fields = ("id", "uuid")
    queryset = Provider.objects.all()
    serializer_class = ProviderSerializer
    http_method_names = ['get', 'post', 'head', 'options', 'trace']

    def get_serializer_class(self):
        if self.action == 'create':
            return POST_ProviderSerializer
        return ProviderSerializer

    def get_queryset(self):
        """
        Filter providers by current user
        """
        user = self.request.user
        # Anonymous access: Show ONLY the providers that are:
        # publically available, active, and non-end dated
        if (type(user) == AnonymousUser):
            return Provider.objects.filter(
                only_current(), active=True, public=True)
        providers = user.current_providers
        # NOTE: This does _NOT_ filter out providers that are InMaintenance.
        return providers

    @detail_route()
    def sizes(self, *args, **kwargs):
        provider = self.get_object()
        self.get_queryset = super(viewsets.ReadOnlyModelViewSet, self).get_queryset
        self.queryset = provider.size_set.get_queryset()
        self.serializer_class = SizeSummarySerializer
        return self.list(self, *args, **kwargs)
