from core.models import ApplicationPatternMatch as ImagePatternMatch

from api.v2.serializers.details import ImageAccessListSerializer
from api.v2.views.base import AuthModelViewSet


class ImageAccessListViewSet(AuthModelViewSet):

    """
    API endpoint that allows instance tags to be viewed
    """
    queryset = ImagePatternMatch.objects.all()
    serializer_class = ImageAccessListSerializer

    filter_fields = ('application__id',)

    def get_queryset(self):
        """
        Filter out tags for deleted instances
        """
        return ImagePatternMatch.objects.filter(application__end_date__isnull=True)
