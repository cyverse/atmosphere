"""
Atmosphere service machine rest api.

"""
import copy

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from threepio import logger

from chromogenic.tasks import machine_export_task

from authentication.decorators import api_auth_token_required

from core.models.machine_export import MachineExport as CoreMachineExport

from api.serializers import MachineExportSerializer


class MachineExportList(APIView):
    """
    Starts the process of bundling a running instance
    """

    @api_auth_token_required
    def get(self, request, provider_id, identity_id):
        """
        """
        all_user_reqs = CoreMachineExport.objects.filter(
            export_owner=request.user)
        serialized_data = MachineExportSerializer(all_user_reqs).data
        response = Response(serialized_data)
        return response

    @api_auth_token_required
    def post(self, request, provider_id, identity_id):
        """
        Create a new object based on DATA
        Start the MachineExportThread if not running
            & Add all images marked 'queued'
        OR
        Add self to MachineExportQueue
        Return to user with "queued"
        """
        #request.DATA is r/o
        data = copy.deepcopy(request.DATA)
        owner = request.user.username
        #Staff members can export on users behalf..
        if data.get('created_for') and request.user.is_staff:
            owner = data.get('created_for')
        data['owner'] = owner
        logger.info(data)
        serializer = MachineExportSerializer(data=data)
        if serializer.is_valid():
            export_request = serializer.save()
            machine_export_task.delay(export_request)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MachineExport(APIView):
    """
    Represents:
        Calls to modify the single machine
    TODO: DELETE when we allow owners to 'end-date' their machine..
    """
    @api_auth_token_required
    def get(self, request, provider_id, identity_id, machine_export_id):
        """
        Lookup the machine information
        (Lookup using the given provider/identity)
        Update on server (If applicable)
        """
        try:
            mach_request = CoreMachineExport.objects.get(id=machine_export_id)
        except CoreMachineExport.DoesNotExist:
            return Response(
                'No machine request with id %s' % machine_export_id,
                status=status.HTTP_404_NOT_FOUND)

        serialized_data = MachineExportSerializer(mach_request).data
        response = Response(serialized_data)
        return response

    @api_auth_token_required
    def patch(self, request, provider_id, identity_id, machine_export_id):
        """
        Meta data changes in 'pending' are OK
        Status change 'pending' --> 'cancel' are OK
        All other changes should FAIL
        """
        #user = request.user
        data = request.DATA
        try:
            mach_request = CoreMachineExport.objects.get(id=machine_export_id)
        except CoreMachineExport.DoesNotExist:
            return Response(
                'No machine request with id %s' % machine_export_id,
                status=status.HTTP_404_NOT_FOUND)

        serializer = MachineExportSerializer(mach_request,
                                             data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @api_auth_token_required
    def put(self, request, provider_id, identity_id, machine_export_id):
        """
        Meta data changes in 'pending' are OK
        Status change 'pending' --> 'cancel' are OK
        All other changes should FAIL
        """
        #user = request.user
        data = request.DATA
        try:
            mach_request = CoreMachineExport.objects.get(id=machine_export_id)
        except CoreMachineExport.DoesNotExist:
            return Response(
                'No machine request with id %s' % machine_export_id,
                status=status.HTTP_404_NOT_FOUND)

        serializer = MachineExportSerializer(mach_request,
                                             data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
