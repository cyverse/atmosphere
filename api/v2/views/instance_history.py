from django.db.models import Q

from rest_framework import filters
import django_filters

from core.models import InstanceStatusHistory

from api.v2.serializers.details import InstanceStatusHistorySerializer
from api.v2.views.base import AuthReadOnlyViewSet

class InstanceFilter(django_filters.FilterSet):
    instance = django_filters.MethodFilter(action='filter_instance_id')
    created_by = django_filters.CharFilter('instance__created_by__username')

    def filter_instance_id(self, queryset, value):
        try:
            int_val = int(value)
            return queryset.filter(
                    Q(instance__provider_alias=int_val)
                    | Q(instance_id=int_val))
        except ValueError:
            #Dealing with a UUID
            return queryset.filter(instance__provider_alias=value)

    class Meta:
        model = InstanceStatusHistory
        fields = ['instance', 'created_by']



class InstanceStatusHistoryViewSet(AuthReadOnlyViewSet):

    """
    API endpoint that allows instance tags to be viewed
    """
    queryset = InstanceStatusHistory.objects.all()
    serializer_class = InstanceStatusHistorySerializer
    ordering = ('-start_date', 'instance__id')
    ordering_fields = ('start_date', 'instance__id')
    filter_class = InstanceFilter
    filter_backends = (filters.OrderingFilter, filters.DjangoFilterBackend)

    def get_queryset(self):
        """
        Filter out tags for deleted instances
        """
        return InstanceStatusHistory.objects.filter(instance__end_date__isnull=True)
