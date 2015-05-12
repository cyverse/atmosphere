from django.db.models import Q
from rest_framework import viewsets

from core.models import ProviderMachine
from core.query import only_current_source_args

from api.v2.serializers.details import ProviderMachineSerializer
from api.v2.views.base import AuthReadOnlyViewSet


#TODO: Determine if "OLD" should be used or not...
#OLD: class ProviderMachineViewSet(viewsets.ModelViewSet):
class ProviderMachineViewSet(AuthReadOnlyViewSet):
    """
    API endpoint that allows instance actions to be viewed or edited.
    """

    queryset = ProviderMachine.objects.all()
    serializer_class = ProviderMachineSerializer
    search_fields = ('application_version__application__id', 'instance_source__created_by__username')
    filter_fields = ('application_version__application__id', 'instance_source__created_by__username')

    def get_queryset(self):
        request_user = self.request.user

        #Showing non-end dated, public ProviderMachines
        public_pms_set = ProviderMachine.objects.filter(*only_current_source_args(), application_version__application__private=False)

        #Showing non-end dated, public ProviderMachines
        shared_pms_set = ProviderMachine.objects.filter(*only_current_source_args(), members__in=request_user.group_set.values('id'))

        #NOTE: Showing 'my pms' EVEN if they are end-dated.
        my_pms_set = ProviderMachine.objects.filter(
                Q(application_version__application__created_by=request_user) | Q(instance_source__created_by=request_user)
            )
        #Order them by date, make sure no dupes.
        return (public_pms_set | shared_pms_set | my_pms_set).distinct().order_by('-instance_source__start_date')
