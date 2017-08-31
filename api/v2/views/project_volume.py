from django.db.models import Q
from django.utils import timezone

from core.models import Volume
from core.query import only_current_source
from api.v2.serializers.details import ProjectVolumeSerializer
from api.v2.views.base import AuthModelViewSet


class ProjectVolumeViewSet(AuthModelViewSet):

    """
    API endpoint that allows instance actions to be viewed or edited.
    """

    queryset = Volume.objects.none()
    serializer_class = ProjectVolumeSerializer
    filter_fields = ('project__id',)

    def get_queryset(self):
        """
        Filter out tags for deleted volumes
        """
        user = self.request.user
        now = timezone.now()
        return Volume.objects.filter(
            only_current_source(),
            project__owner__user=user)
