import django_filters

from rest_framework import filters
from rest_framework.serializers import ValidationError

from core.models import AtmosphereUser, MaintenanceRecord
from core.query import only_current

from api.permissions import CanEditOrReadOnly
from api.v2.serializers.details import MaintenanceRecordSerializer
from api.v2.views.base import AuthOptionalViewSet


class MaintenanceRecordFilterBackend(filters.BaseFilterBackend):
    """
    Filter MaintenanceRecords using the request_user and 'query_params'
    """
    def filter_queryset(self, request, queryset, view):
        request_params = request.query_params
        active = request_params.get('active')
        if isinstance(active, basestring) and active.lower() == 'true'\
                or isinstance(active, bool) and active:
            queryset = MaintenanceRecord.active()
        return queryset

class MaintenanceRecordViewSet(AuthOptionalViewSet):

    """
    API endpoint that allows records to be viewed or edited.
    """
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options', 'trace']
    queryset = MaintenanceRecord.objects.order_by('-start_date')
    permission_classes = (CanEditOrReadOnly,)
    serializer_class = MaintenanceRecordSerializer
    filter_backends = (filters.DjangoFilterBackend, filters.SearchFilter, MaintenanceRecordFilterBackend)
