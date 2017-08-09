from django.db.models import Q
from django.utils import timezone

from core.models import Instance, Provider
from core.query import only_current

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
        active_provider_ids = list(Provider.get_active().values_list('id', flat=True))  # Forces an evaluation
        instances = Instance.shared_with_user(user).filter(created_by_identity__provider__id__in=active_provider_ids).filter(only_current(now))
        return instances
