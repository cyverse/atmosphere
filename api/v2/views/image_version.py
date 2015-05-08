from django.db.models import Q
from rest_framework import viewsets

from core.models import ApplicationVersion as ImageVersion
from core.query import only_current_machines_in_version

from api.v2.serializers.details import ImageVersionSerializer


class ImageVersionViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows instance actions to be viewed or edited.
    """
    queryset = ImageVersion.objects.all()
    serializer_class = ImageVersionSerializer
    search_fields = ('application__id', 'application__created_by__username')
    filter_fields = ('application__id', 'application__created_by__username')

    def get_queryset(self):
        request_user = self.request.user

        #Showing non-end dated, public ImageVersions
        public_pms_set = ImageVersion.objects.filter(only_current_machines_in_version(), application__private=False)

        #Showing non-end dated, shared ImageVersions
        shared_pms_set = ImageVersion.objects.filter(only_current_machines_in_version(), membership__in=request_user.group_set.values('id'))

        #NOTE: Showing 'my pms EVEN if they are end-dated.
        my_pms_set = ImageVersion.objects.filter(
                Q(application__created_by=request_user) | Q(machines__instance_source__created_by=request_user)
            )
        #Order them by date, make sure no dupes.
        return (public_pms_set | shared_pms_set | my_pms_set).distinct().order_by('-machines__instance_source__start_date')
