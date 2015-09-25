from django.contrib.auth.models import AnonymousUser
from rest_framework.decorators import detail_route
from rest_framework import viewsets

from core.models import Provider, Group, IdentityMembership
from core.query import only_current_provider, only_current

from api.permissions import CloudAdminRequired
from api.v2.serializers.details import ProviderSerializer, IdentityMembershipSerializer
from api.v2.serializers.summaries import SizeSummarySerializer
from api.v2.views.base import AuthReadOnlyViewSet


class ProviderViewSet(AuthReadOnlyViewSet):

    """
    API endpoint that allows providers to be viewed or edited.
    """

    queryset = Provider.objects.all()
    serializer_class = ProviderSerializer
    http_method_names = ['get', 'head', 'options', 'trace']


    def get_permissions(self):
        method = self.request.method
        if method == 'DELETE' or method == 'PUT':
            self.permission_classes += (CloudAdminRequired,)
        return super(AuthReadOnlyViewSet, self).get_permissions()

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

        group = Group.objects.get(name=user.username)
        provider_ids = group.identities.filter(
            only_current_provider(),
            provider__active=True).values_list('provider', flat=True)
        return Provider.objects.filter(id__in=provider_ids)

    @detail_route()
    def sizes(self, *args, **kwargs):
        provider = self.get_object()
        self.get_queryset = super(viewsets.ReadOnlyModelViewSet, self).get_queryset
        self.queryset = provider.size_set.get_queryset()
        self.serializer_class = SizeSummarySerializer
        return self.list(self, *args, **kwargs)

    @detail_route()
    def identities(self, *args, **kwargs):
        provider = self.get_object()
        self.get_queryset = super(viewsets.ReadOnlyModelViewSet, self).get_queryset
        self.serializer_class = IdentityMembershipSerializer
        user = self.request.user
        if user.is_staff or user.is_superuser:
            self.queryset = IdentityMembership.objects.filter(identity__provider=provider)
        elif type(user) != AnonymousUser:
            self.queryset = IdentityMembership.objects.filter(identity__provider=provider, identity__created_by=user)
        else:
            self.queryset = IdentityMembership.objects.none()
        return self.list(self, *args, **kwargs)
