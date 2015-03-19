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

    def get_queryset(self):
        """
        Filter out tags for deleted instances
        """
        user = self.request.user
        return ProjectInstance.objects.filter(
            instance__end_date__isnull=True,
            instance__created_by=user
        )
