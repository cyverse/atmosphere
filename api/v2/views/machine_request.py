from core.models import MachineRequest
from core.email import send_denied_resource_email

from web.emails import resource_request_email

from api.v2.serializers.details import MachineRequestSerializer,\
    UserMachineRequestSerializer
from api.v2.views.base import BaseRequestViewSet

class MachineRequestViewSet(BaseRequestViewSet):
    
    def get_queryset(self):
        assert self.model is not None, (
            "%s should include a `model` attribute."
            %self.__class__.__name__
        )
        return self.model.objects.all()

    queryset = MachineRequest.objects.none()
    model = MachineRequest
    serializer_class = UserMachineRequestSerializer
    admin_serializer_class = MachineRequestSerializer
