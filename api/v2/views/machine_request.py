from api import exceptions
from api.v2.serializers.details import MachineRequestSerializer,\
    UserMachineRequestSerializer
from api.v2.views.base import BaseRequestViewSet

from django.db.models import Q

from core import exceptions as core_exceptions
from core.email import send_denied_resource_email
from core.models import MachineRequest, IdentityMembership, AtmosphereUser,\
    Provider, ProviderMachine
from core.models.status_type import StatusType
from core.email import requestImaging

from service.tasks.machine import start_machine_imaging


class MachineRequestViewSet(BaseRequestViewSet):    
    queryset = MachineRequest.objects.none()
    model = MachineRequest
    serializer_class = UserMachineRequestSerializer
    admin_serializer_class = MachineRequestSerializer
    filter_fields = ('status__id', 'status__name', 'new_machine_owner__username')

    def perform_create(self, serializer):

        q = MachineRequest.objects.filter((Q(created_by__id=self.request.user.id) &\
            Q(instance_id=serializer.validated_data['instance'].id) &\
            ~Q(status__name="failed") &\
            ~Q(status__name="rejected") &\
            ~Q(status__name="failed") &\
            ~Q(status__name="closed")))

        if len(q) > 0:
            raise core_exceptions.RequestLimitExceeded("Only one open request per instance is allowed.")

        # NOTE: An identity could possible have multiple memberships
        # It may be better to directly take membership rather than an identity
        identity_id = serializer.initial_data.get("identity")
        new_provider_id= serializer.initial_data['new_machine_provider']
        new_owner_id=self.request.user.id
        parent_machine_id = serializer.validated_data['instance'].provider_machine.id
        status, _ = StatusType.objects.get_or_create(name="pending")
        new_machine_provider = Provider.objects.filter(id=new_provider_id)
        new_machine_owner = AtmosphereUser.objects.filter(id=new_owner_id)
        parent_machine = ProviderMachine.objects.filter(id=parent_machine_id)

        if new_machine_provider.count(): 
            new_machine_provider = new_machine_provider[0]
        else:
            raise exceptions.ParseError(detail="Could not retrieve new machine provider.")

        if new_machine_owner.count():
            new_machine_owner = new_machine_owner[0]
        else:
            raise exceptions.ParseError(detail="Could not retrieve new machine owner.")
        
        if parent_machine.count():
            parent_machine = parent_machine[0]
        else:
            raise exceptions.ParseError(detail="Could not retrieve parent machine.")

        try:
            membership = IdentityMembership.objects.get(identity=identity_id)
            instance = serializer.save(
                membership=membership,
                status=status,
                old_status="pending",
                created_by=self.request.user,
                new_machine_provider = new_machine_provider,
                new_machine_owner = new_machine_owner,
                parent_machine = parent_machine
            )
            self.submit_action(instance)
        except (core_exceptions.ProviderLimitExceeded,
                core_exceptions.RequestLimitExceeded):
            message = "Only one active request is allowed per provider."
            raise exceptions.MethodNotAllowed('create', detail=message)
        except core_exceptions.InvalidMembership:
            message = (
                "The user '%s' is not a valid member."
                % self.request.user.username
            )
            raise exceptions.ParseError(detail=message)
        except IdentityMembership.DoesNotExist:
            message = (
                "The identity '%s' does not have a membership"
                % identity_id
            )
            raise exceptions.ParseError(detail=message)
        except Exception as e:
            message = {
                "An error was encoutered when submitting the request."
            }
            raise exceptions.ParseError(detail=message)

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
