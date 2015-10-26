import django_filters

from core.models import BootScript
from api.v2.serializers.details import BootScriptSerializer
from api.v2.views.base import AuthViewSet
from api.v2.views.mixins import MultipleFieldLookup


class ImageVersionFilter(django_filters.FilterSet):
    version_id = django_filters.CharFilter(
        'application_versions__id')

    class Meta:
        model = BootScript
        fields = ['version_id', 'title']


class BootScriptViewSet(MultipleFieldLookup, AuthViewSet):

    """
    API endpoint that allows scripts to be viewed or edited.
    """

    queryset = BootScript.objects.none()
    serializer_class = BootScriptSerializer
    filter_class = ImageVersionFilter
    search_fields = ('^title',)
    lookup_fields = ('id', 'uuid')

    def get_queryset(self):
        """
        Filter out tags for deleted instances
        """
        user_id = self.request.user.id
        return BootScript.objects.filter(created_by_id=user_id)
