from django.db.models import Q
from django.utils import timezone

from core.models import ProjectInstance, Provider

from api.v2.serializers.details import ProjectInstanceSerializer
from api.v2.views.base import AuthViewSet


class ProjectInstanceViewSet(AuthViewSet):

    """
    API endpoint that allows instance actions to be viewed or edited.
    """

    queryset = ProjectInstance.objects.all()
    serializer_class = ProjectInstanceSerializer
    filter_fields = ('project__id',)

    def get_queryset(self):
        """
        Filter out tags for deleted instances
        """
        user = self.request.user
        now = timezone.now()
        p_instances = ProjectInstance.objects.filter(
            Q(instance__end_date__gt=now) |
            Q(instance__end_date__isnull=True),
            instance__start_date__lt=now,
            project__owner__user=user)
        active_provider_uuids = [ap.uuid for ap in Provider.get_active()]
        return p_instances.filter(
            pk__in=[i.id for i in p_instances
                    if i.instance.provider_uuid() in active_provider_uuids])
