"""
Atmosphere service machine rest api.

"""

from rest_framework.reverse import reverse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from atmosphere.logger import logger
from atmosphere import settings

from auth.decorators import api_auth_token_required

from service.api import prepareDriver, failureJSON
from service.api.serializers import MachineExportSerializer
from core.models.machine_request import MachineExport as CoreMachineExport
from core.models.identity import Identity as CoreIdentity

from web.tasks import machineImagingTask

import copy


class MachineExportList(APIView):
    """
    Starts the process of bundling a running instance
    """

    @api_auth_token_required
    def get(self, request, provider_id, identity_id):
        """
        """
        all_user_reqs = CoreMachineExport.objects.filter(export_owner=request.user)
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
        data.update({'owner':data.get('created_for',request.user.username)})
        logger.info(data)
        serializer = MachineExportSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            export_request = serializer.object
            machineExportTask.delay(export_request)
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
        Lookup the machine information (Lookup using the given provider/identity)
        Update on server (If applicable)
        """
        try:
            mach_request = CoreMachineExport.objects.get(id=machine_export_id)
        except CoreMachineExport.DoesNotExist as no_obj:
            return Response('No machine request with id %s' % machine_export_id, status=status.HTTP_404_NOT_FOUND)

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
        user = request.user
        data = request.DATA
        try:
            mach_request = CoreMachineExport.objects.get(id=machine_export_id)
        except CoreMachineExport.DoesNotExist as no_obj:
            return Response('No machine request with id %s' % machine_export_id, status=status.HTTP_404_NOT_FOUND)

        serializer = MachineExportSerializer(mach_request, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @api_auth_token_required
    def put(self, request, provider_id, identity_id, machine_id):
        """
        Meta data changes in 'pending' are OK
        Status change 'pending' --> 'cancel' are OK
        All other changes should FAIL
        """
        user = request.user
        data = request.DATA
        try:
            mach_request = CoreMachineExport.objects.get(id=machine_export_id)
        except CoreMachineExport.DoesNotExist as no_obj:
            return Response('No machine request with id %s' % machine_export_id, status=status.HTTP_404_NOT_FOUND)

        serializer = MachineExportSerializer(mach_request, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
