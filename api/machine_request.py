"""
Atmosphere service machine rest api.

"""
import copy
import re

from rest_framework.response import Response
from rest_framework import status

from threepio import logger

from core.models.machine_request import share_with_admins, share_with_self
from core.models.machine_request import MachineRequest as CoreMachineRequest
from core.models import Provider

from service.tasks.machine import start_machine_imaging
from service.instance import _permission_to_act
from service.exceptions import ActionNotAllowed

from web.emails import requestImaging

from api import failure_response
from api.serializers import MachineRequestSerializer
from api.views import AuthAPIView


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
        serialized_data = MachineRequestSerializer(all_user_reqs, many=True).data
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
        except Exception, exc:
            return failure_response(
                status.HTTP_400_BAD_REQUEST, exc.message)

    def _permission_to_image(self, machine_request, identity_uuid, instance):
        """
        Raises an exception when imaging has been disabled, OR if
        user attempts to image an instance that is not 'machine' in source.
        """
        instance = machine_request.instance
        if instance.source.is_machine():
            machine = machine_request.instance.source.providermachine
            if not machine.allow_imaging:
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
        # request.DATA is r/o
        # Copy allows for editing
        data = copy.deepcopy(request.DATA)
        data.update({'owner': data.get('created_for', request.user.username)})
        if data.get('vis', 'public') != 'public':
            user_list = re.split(', | |\n', data.get('shared_with', ""))
            share_with_admins(user_list, data.get('provider'))
            share_with_self(user_list, request.user.username)
            user_list = [user for user in user_list if user]  # Skips blanks
            # TODO: Remove duplicates as well..
            data['shared_with'] = user_list
        logger.info(data)
        serializer = MachineRequestSerializer(data=data)
        if serializer.is_valid():
            # Add parent machine to request
            machine_request = serializer.object
            self._permission_to_image(machine_request, identity_uuid)
            instance = machine_request.instance
            machine = machine_request.instance.source.providermachine
            # NOTE: THIS IS A HACK -- While we enforce all images
            #       to go to iPlant Cloud - Tucson.
            # THIS CODE SHOULD BE REMOVED
            try:
                tucson_provider = Provider.objects.get(
                    location='iPlant Cloud - Tucson')
                if machine_request.new_machine_provider.location\
                   != tucson_provider.location:
                    machine_request.new_machine_provider = tucson_provider
            except:
                # Will skip this step if no provider is named
                # iPlant Cloud - Tucson.
                pass
            serializer.save()
            # Object now has an ID for links..
            machine_request_id = serializer.object.id
            active_provider = machine_request.active_provider()
            auto_approve = active_provider.auto_imaging
            requestImaging(request, machine_request.id,
                           auto_approve=auto_approve)
            if auto_approve:
                start_machine_imaging(machine_request)
            return Response(serializer.data,
                            status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)


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
        data = request.DATA
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
            machine_request = serializer.object
            if machine_request.status == 'approve':
                start_machine_imaging(machine_request)
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, provider_uuid, identity_uuid, machine_request_id):
        """
        Authentication Required, update information on a pending request.
        """
        # Meta data changes in 'pending' are OK
        # Status change 'pending' --> 'cancel' are OK
        data = request.DATA
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
            machine_request = serializer.object
            if machine_request.status == 'approve':
                start_machine_imaging(machine_request)
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
