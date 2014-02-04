"""
Atmosphere service machine rest api.

"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import NotAuthenticated
from rest_framework import status

from threepio import logger

from authentication.decorators import api_auth_token_required#, api_auth_options

from api.serializers import MachineRequestSerializer
from core.models.machine_request import share_with_admins, share_with_self
from core.models.machine_request import MachineRequest as CoreMachineRequest

from web.emails import requestImaging
from service.tasks.machine import start_machine_imaging

import copy
import re


class MachineRequestList(APIView):
    """
    This is the user portal for machine requests
    Here they can view all the machine requests they made
    as well as e-mail the admins to approve a machine request
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
        Sends an e-mail to the admins to start
        the create_image process.
        """
        #request.DATA is r/o
        #Copy allows for editing
        data = copy.deepcopy(request.DATA)
        data.update({'owner': data.get('created_for', request.user.username)})
        if data.get('vis','public') != 'public':
            user_list  = re.split(', | |\n', data.get('shared_with',""))
            share_with_admins(user_list, data.get('provider'))
            share_with_self(user_list, request.user.username)
            user_list = [user for user in user_list if user] # Skips blanks
            data['shared_with'] = user_list
        logger.info(data)
        serializer = MachineRequestSerializer(data=data)
        if serializer.is_valid():
            #Add parent machine to request
            machine_request = serializer.object
            machine_request.parent_machine = machine_request.instance.provider_machine
            serializer.save()
            #Object now has an ID for links..
            machine_request_id = serializer.object.id
            requestImaging(request, machine_request_id)
            return Response(serializer.data,
                            status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)

class MachineRequestStaffList(APIView):
    """
    """

    @api_auth_token_required
    def get(self, request):
        """
        """
        if not request.user.is_staff:
            raise NotAuthenticated("Must be a staff user to view requests "
                                   "directly")

        machine_requests = CoreMachineRequest.objects.all()

        serializer = MachineRequestSerializer(machine_requests, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MachineRequestStaff(APIView):
    """
    This is the staff portal for machine requests
    A staff member can view any machine request by its ID
    """

    @api_auth_token_required
    def get(self, request, machine_request_id, action=None):
        """
        OPT 1 for approval: via GET with /approve or /deny
        This is a convenient way to approve requests remotely
        """
        if not request.user.is_staff:
            raise NotAuthenticated("Must be a staff user to view requests "
                                   "directly")

        try:
            machine_request = CoreMachineRequest.objects.get(
                id=machine_request_id)
        except CoreMachineRequest.DoesNotExist:
            return Response('No machine request with id %s'
                            % machine_request_id,
                            status=status.HTTP_404_NOT_FOUND)

        serializer = MachineRequestSerializer(machine_request)
        if not action:
            return Response(serializer.data, status=status.HTTP_200_OK)

        machine_request = serializer.object
        #Don't update the request unless its pending
        if machine_request.status in ['error','pending']:
            machine_request.status = action
            machine_request.save()

        #Only run task if status is 'approve'
        if machine_request.status == 'approve':
            start_machine_imaging(machine_request)

        serializer = MachineRequestSerializer(machine_request)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @api_auth_token_required
    def patch(self, request, machine_request_id, action=None):
        """
        OPT2 for approval: sending a PATCH to the machine request with
          {"status":"approve/deny"}
        
        Modfiy attributes on a machine request
        """
        if not request.user.is_staff:
            raise NotAuthenticated("Must be a staff user to view requests "
                                   "directly")

        try:
            machine_request = CoreMachineRequest.objects.get(
                id=machine_request_id)
        except CoreMachineRequest.DoesNotExist:
            return Response('No machine request with id %s'
                            % machine_request_id,
                            status=status.HTTP_404_NOT_FOUND)

        data = request.DATA
        serializer = MachineRequestSerializer(machine_request, data=data,
                partial=True)
        if serializer.is_valid():
            #Only run task if status is 'approve'
            if machine_request.status == 'approve':
                start_machine_imaging(machine_request)
            machine_request.save()
        #Object may have changed
        serializer = MachineRequestSerializer(machine_request)
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
            machine_request = CoreMachineRequest.objects.get(
                id=machine_request_id)
        except CoreMachineRequest.DoesNotExist:
            return Response('No machine request with id %s'
                            % machine_request_id,
                            status=status.HTTP_404_NOT_FOUND)

        serialized_data = MachineRequestSerializer(machine_request).data
        response = Response(serialized_data)
        return response

    @api_auth_token_required
    def patch(self, request, provider_id, identity_id, machine_request_id):
        """
        Meta data changes in 'pending' are OK
        Status change 'pending' --> 'cancel' are OK
        All other changes should FAIL
        """
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

    @api_auth_token_required
    def put(self, request, provider_id, identity_id, machine_request_id):
        """
        Meta data changes in 'pending' are OK
        Status change 'pending' --> 'cancel' are OK
        All other changes should FAIL
        """
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
            #Only run task if status is 'approve'
            machine_request = serializer.object
            if machine_request.status == 'approve':
                start_machine_imaging(machine_request)
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
