import django_filters
from rest_framework import filters

from api.v2.serializers.details import InstanceActionSerializer
from api.v2.views.base import AuthReadOnlyViewSet
from core.models import InstanceAction, Instance


class InstanceActionFilter(filters.FilterSet):
    provider_id = django_filters.CharFilter(method='filter_by_provider')
    instance_id = django_filters.CharFilter(method='filter_by_instance')

    def filter_by_instance(self, queryset, name, value):
        """
        Filter actions down to those available for a specific instance
        """
        return InstanceAction.filter_by_instance(value, queryset)

    def filter_by_provider(self, queryset, name, value):
        """
        Filter actions down to those available for a specific provider
        """
        return InstanceAction.filter_by_provider(value, queryset)

    class Meta:
        model = InstanceAction
        fields = ['provider_id', 'instance_id']


class InstanceActionViewSet(AuthReadOnlyViewSet):
    """
    API endpoint that shows all known instance actions
    - Instance action usage is based on instance state and provider config.
    """
    queryset = InstanceAction.objects.all()
    serializer_class = InstanceActionSerializer
    filter_class = InstanceActionFilter
