from rest_framework import filters
import django_filters

from core.models import ApplicationVersion as ImageVersion
from api.v2.views.base import AuthOptionalViewSet
from api.v2.serializers.details import ImageVersionSerializer


class ImageVersionFilter(django_filters.FilterSet):
    image_id = django_filters.CharFilter('application__id')
    created_by = django_filters.CharFilter('application__created_by__username')

    class Meta:
        model = ImageVersion
        fields = ['image_id', 'created_by']


class ImageVersionViewSet(AuthOptionalViewSet):

    """
    API endpoint that allows instance actions to be viewed or edited.
    """
    queryset = ImageVersion.objects.all()
    serializer_class = ImageVersionSerializer
    search_fields = ('application__id', 'application__created_by__username')
    ordering_fields = ('start_date',)
    ordering = ('start_date',)
    filter_class = ImageVersionFilter
    filter_backends = (filters.OrderingFilter, filters.DjangoFilterBackend)

    def get_queryset(self):
        request_user = self.request.user
        return ImageVersion.current_machines(request_user)
