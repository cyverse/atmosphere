from core.models import ProjectVolume

from api.v2.serializers.details import ProjectVolumeSerializer
from api.v2.base import AuthViewSet


class ProjectVolumeViewSet(AuthViewSet):
    """
    API endpoint that allows instance actions to be viewed or edited.
    """

    queryset = ProjectVolume.objects.all()
    serializer_class = ProjectVolumeSerializer
    filter_fields = ('project__id',)
    # http_method_names = ['get', 'post', 'delete', 'head', 'options', 'trace']

    def get_queryset(self):
        """
        Filter out tags for deleted volumes
        """
        user = self.request.user
        return ProjectVolume.objects.filter(
            volume__instance_source__end_date__isnull=True,
            volume__instance_source__created_by=user
        )
