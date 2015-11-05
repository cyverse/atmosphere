from core.models import ApplicationTag as ImageTag

from api.v2.serializers.details import ImageTagSerializer
from api.v2.views.base import AuthViewSet


class ImageTagViewSet(AuthViewSet):

    """
    API endpoint that allows instance tags to be viewed
    """
    queryset = ImageTag.objects.all()
    serializer_class = ImageTagSerializer

    filter_fields = ('application__id',)

    def get_queryset(self):
        """
        Filter out tags for deleted instances
        """
        return ImageTag.objects.filter(application__end_date__isnull=True)
