from core.models import MachineRequest
from core.email import send_denied_resource_email

from web.emails import resource_request_email

from django.db.models import Q

from api.v2.serializers.details import MachineRequestSerializer,\
    UserMachineRequestSerializer
from api.v2.views.base import BaseRequestViewSet

class MachineRequestViewSet(BaseRequestViewSet):
    
    def get_queryset(self):
        username = self.request.query_params.get('username')
        assert self.model is not None, (
            "%s should include a `model` attribute."
            %self.__class__.__name__
        )
        if(username is not None):
            return self.model.objects.filter(new_machine_owner__username=username)
        return self.model.objects.filter(~Q(status__in=["completed", "skipped", "deny"]))

    queryset = MachineRequest.objects.none()
    model = MachineRequest
    serializer_class = UserMachineRequestSerializer
    admin_serializer_class = MachineRequestSerializer
