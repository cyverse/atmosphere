from django.db.models import Q
from django.utils import timezone

from core.models import ProjectApplication, Provider

from api.v2.serializers.details import ProjectApplicationSerializer
from api.v2.views.base import AuthViewSet


class ProjectApplicationViewSet(AuthViewSet):

    """
    API endpoint that allows application actions to be viewed or edited.
    """

    queryset = ProjectApplication.objects.all()
    serializer_class = ProjectApplicationSerializer
    filter_fields = ('project__id',)

    def get_queryset(self):
        """
        Filter out tags for deleted applications
        """
        user = self.request.user
        now = timezone.now()
        p_applications = ProjectApplication.objects.filter(
            Q(application__end_date__gt=now) |
            Q(application__end_date__isnull=True),
            application__start_date__lt=now,
            application__created_by=user)
        active_provider_uuids = [ap.uuid for ap in Provider.get_active()]
        return p_applications.filter(
            pk__in=[i.id for i in p_applications
                    if i.application.provider_uuid() in active_provider_uuids])
