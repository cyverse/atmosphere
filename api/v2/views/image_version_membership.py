from django.db.models import Q
import django_filters

from core.models import ApplicationVersionMembership as ImageVersionMembership

from api.v2.serializers.details import ImageVersionMembershipSerializer
from api.v2.views.base import AuthViewSet

class VersionFilter(django_filters.FilterSet):
    version_id = django_filters.MethodFilter(action='filter_by_uuid')
    created_by = django_filters.MethodFilter(action='filter_owner')

    def filter_owner(self, queryset, value):
        return queryset.filter(
            Q(application_version__created_by__username=value) |
            Q(application_version__application__created_by__username=value)
        )
    def filter_by_uuid(self, queryset, value):
        # NOTE: Remove this *HACK* once django_filters supports UUID as PK fields
        return queryset.filter(application_version__id=value)

    class Meta:
        model = ImageVersionMembership
        fields = ['version_id', 'created_by']


class ImageVersionMembershipViewSet(AuthViewSet):

    """
    API endpoint that allows version tags to be viewed
    """
    queryset = ImageVersionMembership.objects.none()
    serializer_class = ImageVersionMembershipSerializer
    filter_class = VersionFilter

    def get_queryset(self):
        """
        Filter out tags for deleted versions
        """
        return ImageVersionMembership.objects.filter(
            application_version__created_by=self.request.user)
