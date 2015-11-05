from rest_framework import filters
import django_filters

from core.models.cloud_admin import admin_provider_list
from core.models import IdentityMembership, Group
from core.query import only_active_provider_memberships

from api.v2.serializers.details import IdentityMembershipSerializer
from api.v2.views.base import AdminAuthViewSet


class IdentityMembershipFilter(django_filters.FilterSet):
    provider_id = django_filters.CharFilter('identity__provider__id')
    username = django_filters.CharFilter(
        'identity__created_by__username', lookup_type='icontains')
    class Meta:
        model = IdentityMembership
        fields = ['provider_id', 'username']

class IdentityMembershipViewSet(AdminAuthViewSet):

    """
    API endpoint that allows providers to be viewed or edited.
    """
    queryset = IdentityMembership.objects.all()
    serializer_class = IdentityMembershipSerializer
    filter_class = IdentityMembershipFilter
    filter_backends = (filters.OrderingFilter, filters.DjangoFilterBackend)
    http_method_names = [
            'get', 'patch', 'put'
            'head', 'options', 'trace']

    def get_queryset(self):
        """
        Filter identities by current user
        """
        user = self.request.user
        if user.is_superuser or user.is_staff:
            return IdentityMembership.objects.filter(
                    only_active_provider_memberships())
        # Limit to the accounts you are an administrator of
        providers = admin_provider_list(user)
        return IdentityMembership.objects.filter(
                identity__provider__in=providers)
