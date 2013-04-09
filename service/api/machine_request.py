"""
Atmosphere service machine rest api.

"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from atmosphere.logger import logger
from atmosphere import settings

from authentication.decorators import api_auth_token_required

from service.api.serializers import MachineRequestSerializer
from core.models.machine_request import MachineRequest as CoreMachineRequest

from web.emails import requestImaging
from service.tasks.machine import machineImagingTask

import copy


class MachineRequestList(APIView):
    """
    Starts the process of bundling a running instance
    """

    @api_auth_token_required
    def get(self, request, provider_id, identity_id):
        """
        """
        all_user_reqs = CoreMachineRequest.objects.filter(
            new_machine_owner=request.user)
        serialized_data = MachineRequestSerializer(all_user_reqs).data
        response = Response(serialized_data)
        return response

    @api_auth_token_required
    def post(self, request, provider_id, identity_id):
        """
        Create a new object based on DATA
        Start the MachineRequestThread if not running
            & Add all images marked 'queued'
        OR
        Add self to MachineRequestQueue
        Return to user with "queued"
        """
        #request.DATA is r/o
        #Copy allows for editing
        data = copy.deepcopy(request.DATA)
        data.update({'owner': data.get('created_for', request.user.username)})
        logger.info(data)
        serializer = MachineRequestSerializer(data=data)
        if serializer.is_valid():
            obj = serializer.object
            obj.parent_machine = obj.instance.provider_machine
            serializer.save()
            machine_request_id = serializer.object.id
            approve_link = '%s/api/request_image/%s/approve' \
                % (settings.SERVER_URL, machine_request_id)
            deny_link = '%s/api/request_image/%s/deny' \
                % (settings.SERVER_URL, machine_request_id)
            requestImaging(request, approve_link, deny_link)
            return Response(serializer.data,
                            status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)


class MachineRequestAction(APIView):
    """
    Starts the process of bundling a running instance
    """

    @api_auth_token_required
    def get(self, request, machine_request_id, action):
        """
        """
        try:
            mach_request = CoreMachineRequest.objects.get(
                id=machine_request_id)
        except CoreMachineRequest.DoesNotExist:
            return Response('No machine request with id %s'
                            % machine_request_id,
                            status=status.HTTP_404_NOT_FOUND)

        serializer = MachineRequestSerializer(mach_request)
        machine_request = serializer.object
        #Don't update the request unless its pending
        if machine_request.status == 'pending':
            machine_request.status = action
        serializer.save()
        #Only run task if status is 'approve'
        if machine_request.status == 'approve':
            machine_request.status = 'queued'
            serializer.save()
            machineImagingTask.delay(machine_request)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MachineRequest(APIView):
    """
    Represents:
        Calls to modify the single machine
    TODO: DELETE when we allow owners to 'end-date' their machine..
    """
    @api_auth_token_required
    def get(self, request, provider_id, identity_id, machine_request_id):
        """
        Lookup the machine information
        (Lookup using the given provider/identity)
        Update on server (If applicable)
        """
        try:
            mach_request = CoreMachineRequest.objects.get(
                id=machine_request_id)
        except CoreMachineRequest.DoesNotExist:
            return Response('No machine request with id %s'
                            % machine_request_id,
                            status=status.HTTP_404_NOT_FOUND)

        serialized_data = MachineRequestSerializer(mach_request).data
        response = Response(serialized_data)
        return response

    @api_auth_token_required
    def patch(self, request, provider_id, identity_id, machine_request_id):
        """
        Meta data changes in 'pending' are OK
        Status change 'pending' --> 'cancel' are OK
        All other changes should FAIL
        """
        #user = request.user
        data = request.DATA
        try:
            mach_request = CoreMachineRequest.objects.get(
                id=machine_request_id)
        except CoreMachineRequest.DoesNotExist:
            return Response('No machine request with id %s'
                            % machine_request_id,
                            status=status.HTTP_404_NOT_FOUND)

        serializer = MachineRequestSerializer(mach_request,
                                              data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @api_auth_token_required
    def put(self, request, provider_id, identity_id, machine_request_id):
        """
        Meta data changes in 'pending' are OK
        Status change 'pending' --> 'cancel' are OK
        All other changes should FAIL
        """
        #user = request.user
        data = request.DATA
        try:
            mach_request = CoreMachineRequest.objects.get(
                id=machine_request_id)
        except CoreMachineRequest.DoesNotExist:
            return Response('No machine request with id %s'
                            % machine_request_id,
                            status=status.HTTP_404_NOT_FOUND)

        serializer = MachineRequestSerializer(mach_request,
                                              data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
