"""
Atmosphere service machine rest api.

"""
import copy
import re

from rest_framework.response import Response
from rest_framework import status

from threepio import logger

from core.models.machine_request import MachineRequest as CoreMachineRequest
from core.models import Provider
from core.models import IdentityMembership
from core.models.status_type import StatusType

from service.instance import _permission_to_act
from service.exceptions import ActionNotAllowed
from service.machine import share_with_admins, share_with_self
from service.tasks.machine import start_machine_imaging

from core.email import requestImaging

from api import failure_response
from api.exceptions import bad_request
from api.v1.serializers import MachineRequestSerializer
from api.v1.views.base import AuthAPIView

from django.conf import settings

class MachineRequestList(AuthAPIView):

    """
    This is the user portal for machine requests
    Here they can view all the machine requests they made
    as well as e-mail the admins to approve a machine request
    """

    def get(self, request, provider_uuid, identity_uuid):
        """
        """
        all_user_reqs = CoreMachineRequest.objects.filter(
            new_machine_owner=request.user)
        serialized_data = MachineRequestSerializer(
            all_user_reqs,
            many=True).data
        response = Response(serialized_data)
        return response

    def post(self, request, provider_uuid, identity_uuid):
        """
        Sends an e-mail to the admins to start
        the create_image process.
        """
        try:
            return self._create_image(request, provider_uuid, identity_uuid)
        except ActionNotAllowed:
            return failure_response(
                status.HTTP_409_CONFLICT,
                "Machine Imaging has been "
                "explicitly disabled on this provider.")
        except Exception as exc:
            logger.exception(exc)
            return failure_response(
                status.HTTP_400_BAD_REQUEST, exc.message)

    def _permission_to_image(self, identity_uuid, instance):
        """
        Raises an exception when imaging has been disabled, OR if
        user attempts to image an instance that is not 'machine' in source.
        """
        instance = instance
        if instance.source.is_machine():
            machine = instance.source.providermachine
            if not machine.application_version.allow_imaging:
                raise Exception(
                    "The Image Author has disabled re-imaging of Machine %s."
                    % machine.instance_source.identifier)
        elif instance.source.is_volume():
            raise Exception(
                "Instance of booted volume can NOT be imaged."
                "Contact your Administrator for more information.")
        else:
            raise Exception(
                "Instance source type cannot be determined."
                "Contact your Administrator for more information.")

    def _create_image(self, request, provider_uuid, identity_uuid):
        _permission_to_act(identity_uuid, "Imaging")
        # request.data is r/o
        # Copy allows for editing
        data = copy.deepcopy(request.data)
        data.update({'owner': data.get('created_for', request.user.username)})
        if data.get('vis', 'public') != 'public':
            user_list = data.get('shared_with', '')
            if type(user_list) == str:
                user_list = re.split(', | |\n', user_list)
            share_with_admins(user_list, data.get('provider'))
            share_with_self(user_list, request.user.username)
            user_list = [user for user in user_list if user]  # Skips blanks
            # TODO: Remove duplicates as well..
            data['shared_with'] = user_list
        logger.info(data)
        serializer = MachineRequestSerializer(data=data)
        if serializer.is_valid():
            # Add parent machine to request
            instance = serializer.validated_data['instance']
            parent_machine = instance.source.providermachine
            serializer.validated_data['parent_machine'] = parent_machine
            user = serializer.validated_data['new_machine_owner']
            identity_member = IdentityMembership.objects.get(
                    identity__provider=serializer.validated_data['new_machine_provider'],
                    identity__created_by=user)
            serializer.validated_data['membership'] = identity_member
            serializer.validated_data['created_by'] = user
            self._permission_to_image(identity_uuid, instance)
            pending_status = StatusType.objects.get(name='pending')
            machine_request = serializer.save(status=pending_status)
            instance = machine_request.instance
            if hasattr(settings, 'REPLICATION_PROVIDER_LOCATION'):
                try:
                    replication_provider = Provider.objects.get(
                        location=settings.REPLICATION_PROVIDER_LOCATION)
                    if machine_request.new_machine_provider.location\
                       != replication_provider.location:
                        machine_request.new_machine_provider = replication_provider
                except:
                    # Will skip this step if no provider is named
                    # as the REPLICATION_PROVIDER_LOCATION
                    pass
            # Object now has an ID for links..
            machine_request_id = machine_request.id
            active_provider = machine_request.active_provider()
            auto_approve = active_provider.auto_imaging
            requestImaging(request, machine_request_id,
                           auto_approve=auto_approve)
            if auto_approve:
                start_machine_imaging(machine_request)
            return Response(serializer.data,
                            status=status.HTTP_201_CREATED)
        else:
            return bad_request(serializer.errors, prefix="Invalid value for ")


class MachineRequest(AuthAPIView):

    """
    MachineRequests are available to allow users
    to request that their instance be permanantly saved,
    so that it can be re-launched as a new Application at a later date.
    Upon request, these applications can be made Public, Private, or available
    to a specific set of users.
    """

    def get(self, request, provider_uuid, identity_uuid, machine_request_id):
        """
        Authentication Required, get information about a previous request.
        """
        try:
            machine_request = CoreMachineRequest.objects.get(
                id=machine_request_id)
        except CoreMachineRequest.DoesNotExist:
            return Response('No machine request with id %s'
                            % machine_request_id,
                            status=status.HTTP_404_NOT_FOUND)

        serialized_data = MachineRequestSerializer(machine_request).data
        response = Response(serialized_data)
        return response

    def patch(self, request, provider_uuid, identity_uuid,
              machine_request_id):
        """
        Authentication Required, update information on a pending request.
        """
        # Meta data changes in 'pending' are OK
        # Status change 'pending' --> 'cancel' are OK
        data = request.data
        try:
            machine_request = CoreMachineRequest.objects.get(
                id=machine_request_id)
        except CoreMachineRequest.DoesNotExist:
            return Response('No machine request with id %s'
                            % machine_request_id,
                            status=status.HTTP_404_NOT_FOUND)

        serializer = MachineRequestSerializer(machine_request,
                                              data=data, partial=True)
        if serializer.is_valid():
            machine_request = serializer.save()
            if machine_request.old_status == 'approve':
                start_machine_imaging(machine_request)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, provider_uuid, identity_uuid, machine_request_id):
        """
        Authentication Required, update information on a pending request.
        """
        # Meta data changes in 'pending' are OK
        # Status change 'pending' --> 'cancel' are OK
        data = request.data
        try:
            machine_request = CoreMachineRequest.objects.get(
                id=machine_request_id)
        except CoreMachineRequest.DoesNotExist:
            return Response('No machine request with id %s'
                            % machine_request_id,
                            status=status.HTTP_404_NOT_FOUND)

        serializer = MachineRequestSerializer(machine_request,
                                              data=data, partial=True)
        if serializer.is_valid():
            # Only run task if status is 'approve'
            machine_request = serializer.save()
            if machine_request.old_status == 'approve':
                start_machine_imaging(machine_request)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
