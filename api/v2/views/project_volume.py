from rest_framework import viewsets
from core.models import ProjectVolume
from api.v2.serializers.details import ProjectVolumeSerializer


class ProjectVolumeViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows instance actions to be viewed or edited.
    """
    queryset = ProjectVolume.objects.all()
    serializer_class = ProjectVolumeSerializer
    filter_fields = ('project__id',)
    # http_method_names = ['get', 'post', 'delete', 'head', 'options', 'trace']
