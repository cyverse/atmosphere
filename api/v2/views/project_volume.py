from django.db.models import Q
from django.utils import timezone

from core.models import ProjectVolume

from api.v2.serializers.details import ProjectVolumeSerializer
from api.v2.views.base import AuthViewSet


class ProjectVolumeViewSet(AuthViewSet):

    """
    API endpoint that allows instance actions to be viewed or edited.
    """

    queryset = ProjectVolume.objects.none()
    serializer_class = ProjectVolumeSerializer
    filter_fields = ('project__id',)

    def get_queryset(self):
        """
        Filter out tags for deleted volumes
        """
        user = self.request.user
        now = timezone.now()
        # TODO: Refactor -- core.query
        return ProjectVolume.objects.filter(
            Q(volume__instance_source__end_date__gt=now)
            | Q(volume__instance_source__end_date__isnull=True),
            Q(volume__instance_source__provider__end_date__gt=now)
            | Q(volume__instance_source__provider__end_date__isnull=True),
            volume__instance_source__provider__active=True,
            volume__instance_source__start_date__lt=now,
            volume__instance_source__provider__start_date__lt=now,
            project__owner__user=user)
