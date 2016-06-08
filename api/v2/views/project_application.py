from django.db.models import Q
from django.utils import timezone

from core.models import ProjectApplication, Provider, Application

from api.v2.serializers.details import ProjectApplicationSerializer
from api.v2.views.base import AuthViewSet


class ProjectApplicationViewSet(AuthViewSet):

    """
    API endpoint that allows application actions to be viewed or edited.
    """

    queryset = ProjectApplication.objects.all()
    serializer_class = ProjectApplicationSerializer
    filter_fields = ('project__id','application__id')

    def get_queryset(self):
        """
        Filter out ProjectApplications that
        aren't in a project you have access to.
        """
        user = self.request.user
        p_applications = ProjectApplication.objects.filter(project__owner__user=user)
        return p_applications
