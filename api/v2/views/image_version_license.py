from django.db.models import Q
import django_filters

from core.models import ApplicationVersionLicense as ImageVersionLicense

from api.v2.serializers.details import ImageVersionLicenseSerializer
from api.v2.views.base import AuthModelViewSet

class VersionFilter(django_filters.FilterSet):
    version_id = django_filters.CharFilter(method='filter_by_uuid')
    created_by = django_filters.CharFilter(method='filter_owner')

    def filter_owner(self, queryset, name, value):
        return queryset.filter(
            Q(image_version__created_by__username=value) |
            Q(image_version__application__created_by__username=value)
        )
    def filter_by_uuid(self, queryset, name, value):
        # NOTE: Remove this *HACK* once django_filters supports UUID as PK fields
        return queryset.filter(image_version__id=value)

    class Meta:
        model = ImageVersionLicense
        fields = ['version_id', 'created_by']


class ImageVersionLicenseViewSet(AuthModelViewSet):

    """
    API endpoint that allows version tags to be viewed
    """
    queryset = ImageVersionLicense.objects.none()
    serializer_class = ImageVersionLicenseSerializer
    filter_class = VersionFilter

    def get_queryset(self):
        """
        Filter out tags for deleted versions
        """
        return ImageVersionLicense.objects.filter(
            image_version__created_by=self.request.user)
