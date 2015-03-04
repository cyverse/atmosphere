from rest_framework import viewsets
from core.models import ProjectInstance
from api.v2.serializers.details import ProjectInstanceSerializer


class ProjectInstanceViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows instance actions to be viewed or edited.
    """
    queryset = ProjectInstance.objects.all()
    serializer_class = ProjectInstanceSerializer
    filter_fields = ('project__id',)
    # http_method_names = ['get', 'post', 'delete', 'head', 'options', 'trace']
