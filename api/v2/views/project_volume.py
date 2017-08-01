from django.db.models import Q
from django.utils import timezone

from core.models import Volume

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
        # TODO: Refactor -- core.query
        return Volume.objects.filter(
            Q(instance_source__end_date__gt=now)
            | Q(instance_source__end_date__isnull=True),
            Q(instance_source__provider__end_date__gt=now)
            | Q(instance_source__provider__end_date__isnull=True),
            instance_source__provider__active=True,
            instance_source__start_date__lt=now,
            instance_source__provider__start_date__lt=now,
            project__owner__user=user)
