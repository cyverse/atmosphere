import django_filters
import uuid

from rest_framework import filters

from api.v2.serializers.details import InstanceActionSerializer
from api.v2.views.base import AuthReadOnlyViewSet
from core.models import InstanceAction, Instance


class InstanceActionFilter(filters.FilterSet):
    provider_id = django_filters.MethodFilter(action='filter_by_provider')
    instance_id = django_filters.MethodFilter(action='filter_by_instance')

    def filter_by_instance(self, queryset, value):
        """
        Filter actions down to those available for a specific instance
        """
        return InstanceAction.filter_by_instance(value, queryset)

    def filter_by_provider(self, queryset, value):
        """
        Filter actions down to those available for a specific provider
        """
        return InstanceAction.filter_by_provider(value, queryset)

    class Meta:
        model = InstanceAction
        fields = ['provider_id', 'instance_id']


class InstanceActionViewSet(AuthReadOnlyViewSet):
    """
    API endpoint that allows instance actions to be viewed
    """
    queryset = InstanceAction.valid_actions.all()
    serializer_class = InstanceActionSerializer
