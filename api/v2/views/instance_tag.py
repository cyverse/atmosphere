from core.models import InstanceTag

from api.v2.serializers.details import InstanceTagSerializer
from api.v2.views.base import AuthViewSet


class InstanceTagViewSet(AuthViewSet):

    """
    API endpoint that allows instance tags to be viewed
    """
    queryset = InstanceTag.objects.all()
    serializer_class = InstanceTagSerializer
    filter_fields = ('instance__id',)

    def get_queryset(self):
        """
        Filter out tags for deleted instances
        """
        return InstanceTag.objects.filter(instance__end_date__isnull=True)
