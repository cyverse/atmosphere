from django.db.models import Q
import django_filters

from core.models import ProjectMembership
from api.v2.serializers.details import ProjectMembershipSerializer
from api.v2.views.base import AuthViewSet


class ProjectFilter(django_filters.FilterSet):
    project_id = django_filters.MethodFilter(action='filter_by_uuid')
    name = django_filters.MethodFilter(action='filter_by_groupname')

    def filter_by_groupname(self, queryset, value):
        return queryset.filter(
            Q(project__owner__name=value) |
            Q(group__name=value)
        )

    def filter_by_uuid(self, queryset, value):
        # FIXME: Remove *HACK* once django_filters supports UUID as PK fields
        return queryset.filter(project__uuid=value)

    class Meta:
        model = ProjectMembership
        fields = ['project_id', 'name']


class ProjectMembershipViewSet(AuthViewSet):

    """
    API endpoint that allows version tags to be viewed
    """
    queryset = ProjectMembership.objects.none()
    serializer_class = ProjectMembershipSerializer
    filter_class = ProjectFilter

    def get_queryset(self):
        """
        Filter out tags for deleted versions
        """
        return ProjectMembership.objects.filter(
            project__owner__user=self.request.user)
