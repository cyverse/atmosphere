from api.v2.serializers.details import MachineRequestSerializer,\
    UserMachineRequestSerializer
from api.v2.views.base import BaseRequestViewSet
from core.email import send_denied_resource_email
from core.models import MachineRequest
from core.models.status_type import StatusType
from service.tasks.machine import start_machine_imaging
from web.emails import requestImaging


class MachineRequestViewSet(BaseRequestViewSet):    
    queryset = MachineRequest.objects.none()
    model = MachineRequest
    serializer_class = UserMachineRequestSerializer
    admin_serializer_class = MachineRequestSerializer
    filter_fields = ('status__id', 'status__name')

    def submit_action(self, instance):
        """
        Submits a resource request email
        """
        provider = instance.active_provider()
        pre_approved = provider.auto_imaging
        requestImaging(self.request, instance.id, auto_approve=pre_approved)
        
        if pre_approved:
            status, _ = StatusType.objects.get_or_create(name="approved")
            instance.status = status
            instance.save()
            start_machine_imaging(instance)

    def approve_action(self, instance):
        """
        Updates the resource for the request
        """
        start_machine_imaging(instance)

    def deny_action(self, instance):
        """
        Notify the user that the request was denied
        """