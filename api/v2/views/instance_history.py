from django.db.models import Q

from rest_framework import filters
import django_filters

from core.models import InstanceStatusHistory

from api.v2.serializers.details import InstanceStatusHistorySerializer
from api.v2.views.base import AuthReadOnlyViewSet
from api.v2.views.mixins import MultipleFieldLookup

class InstanceStatusHistoryFilter(django_filters.FilterSet):
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



class InstanceStatusHistoryViewSet(MultipleFieldLookup, AuthReadOnlyViewSet):

    """
    API endpoint that allows instance tags to be viewed
    """
    queryset = InstanceStatusHistory.objects.all()
    serializer_class = InstanceStatusHistorySerializer
    ordering = ('-instance__start_date', 'instance__id')
    ordering_fields = ('-instance__start_date', '-start_date', 'instance__id')
    lookup_fields = ("id", "uuid")
    filter_class = InstanceStatusHistoryFilter
    filter_backends = (filters.OrderingFilter, filters.DjangoFilterBackend)

    def get_queryset(self):
        """
        Filter out tags for deleted instances
        """
        user_id = self.request.user.id

        if self.request.query_params.get('unique', "").lower() == 'true':
            # filtering distinct instance__start_date effectively gives us a unique instance list. Also the order of fields in distinct() 
            # must match the order of fields in ordering set above
            return InstanceStatusHistory.objects.filter(instance__created_by_id=user_id).distinct('instance__start_date')

        return InstanceStatusHistory.objects.filter(instance__created_by_id=user_id)
