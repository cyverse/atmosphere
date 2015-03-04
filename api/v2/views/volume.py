import django_filters
from rest_framework import viewsets
from core.models import Volume
from api.v2.serializers.details import VolumeSerializer
from core.query import only_current_source


class VolumeFilter(django_filters.FilterSet):
    min_size = django_filters.NumberFilter(name="size", lookup_type='gte')
    max_size = django_filters.NumberFilter(name="size", lookup_type='lte')

    class Meta:
        model = Volume
        fields = ['min_size', 'max_size', 'projects']


class VolumeViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows providers to be viewed or edited.
    """
    queryset = Volume.objects.all()
    serializer_class = VolumeSerializer
    filter_class = VolumeFilter

    def get_queryset(self):
        """
        Filter projects by current user
        """
        user = self.request.user
        return Volume.objects.filter(only_current_source(), instance_source__created_by=user)
