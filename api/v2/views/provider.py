from django.contrib.auth.models import AnonymousUser
from rest_framework.decorators import detail_route
from rest_framework import viewsets

from core.models import Provider, Group
from core.query import only_current_provider, only_current

from api.v2.serializers.details import ProviderSerializer
from api.v2.serializers.post import ProviderSerializer as POST_ProviderSerializer
from api.v2.serializers.summaries import SizeSummarySerializer
from api.v2.views.base import AuthViewSet
from api.v2.views.mixins import MultipleFieldLookup


class ProviderViewSet(MultipleFieldLookup, AuthViewSet):
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
        method = self.request.method
        admin_qs = Provider.objects.filter(cloud_admin=user)
        # User modify/create/delete queryset:
        if method in ['DELETE', 'PUT', 'POST']:
            return admin_qs
        # User get queryset: Show *shared* + *admin*
        try:
            group = Group.objects.get(name=user.username)
            provider_ids = group.identities.filter(
                only_current_provider(),
                provider__active=True).values_list('provider', flat=True)
            shared_qs = Provider.objects.filter(id__in=provider_ids)
        except Group.DoesNotExist:
            shared_qs = Provider.objects.none()
        queryset = shared_qs | admin_qs
        return queryset

    @detail_route()
    def sizes(self, *args, **kwargs):
        provider = self.get_object()
        self.get_queryset = super(viewsets.ReadOnlyModelViewSet, self).get_queryset
        self.queryset = provider.size_set.get_queryset()
        self.serializer_class = SizeSummarySerializer
        return self.list(self, *args, **kwargs)
