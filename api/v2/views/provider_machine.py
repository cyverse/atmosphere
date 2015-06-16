from django.db.models import Q
from django.contrib.auth.models import AnonymousUser

from core.models import ProviderMachine
from core.query import only_current_source

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
        public_pms_set = ProviderMachine.objects.filter(only_current_source(), application_version__application__private=False)
        if type(request_user) != AnonymousUser:
            #Showing non-end dated, public ProviderMachines
            shared_pms_set = ProviderMachine.objects.filter(only_current_source(), members__in=request_user.group_set.values('id'))
            #NOTE: Showing 'my pms' EVEN if they are end-dated.
            my_pms_set = ProviderMachine.objects.filter(
                    Q(application_version__application__created_by=request_user) | Q(instance_source__created_by=request_user)
                )
        else:
            shared_pms_set = ProviderMachine.objects.none()
            my_pms_set = ProviderMachine.objects.none()
        #Order them by date, make sure no dupes.
        return (public_pms_set | shared_pms_set | my_pms_set).distinct().order_by('-instance_source__start_date')
