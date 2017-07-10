from django.db.models import Q
from django.utils import timezone

from core.models import Instance, Provider

from api.v2.serializers.details import ProjectInstanceSerializer
from api.v2.views.base import AuthModelViewSet


class ProjectInstanceViewSet(AuthModelViewSet):

    """
    API endpoint that allows instance actions to be viewed or edited.
    """

    queryset = Instance.objects.all()
    serializer_class = ProjectInstanceSerializer
    filter_fields = ('project__id',)

    def get_queryset(self):
        """
        Filter out tags for deleted instances
        """
        user = self.request.user
        now = timezone.now()
        instances = Instance.objects.filter(
            Q(end_date__gt=now) |
            Q(end_date__isnull=True),
            start_date__lt=now,
            project__owner__user=user)
        active_provider_uuids = [ap.uuid for ap in Provider.get_active()]
        return instances.filter(
            pk__in=[i.id for i in instances
                    if i.provider_uuid() in active_provider_uuids])
