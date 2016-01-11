from rest_framework.serializers import ValidationError

from core.models import MaintenanceRecord

from api.permissions import CanEditOrReadOnly
from api.v2.serializers.details import MaintenanceRecordSerializer
from api.v2.views.base import AuthOptionalViewSet


class MaintenanceRecordViewSet(AuthOptionalViewSet):

    """
    API endpoint that allows records to be viewed or edited.
    """
    http_method_names = ['get', 'post', 'put', 'patch', 'head', 'options', 'trace']
    max_paginate_by = 1000
    queryset = MaintenanceRecord.objects.order_by('-start_date')
    permission_classes = (CanEditOrReadOnly,)
    serializer_class = MaintenanceRecordSerializer
