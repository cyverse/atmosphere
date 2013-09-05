"""
Atmosphere service maintenance record rest api.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from threepio import logger

from authentication.decorators import api_auth_token_required

from api.serializers import MaintenanceRecordSerializer
from core.models.maintenance import MaintenanceRecord as CoreMaintenanceRecord

import copy

from django.utils import timezone


class MaintenanceRecordList(APIView):
    """
    Starts the process of bundling a running instance
    """

    @api_auth_token_required
    def get(self, request):
        """
        """
        records = CoreMaintenanceRecord.objects.all()
        if 'active' in request.GET:
            now_time = timezone.now()
            records = records.filter(start_date__gte=now_time)
        serialized_data = MaintenanceRecordSerializer(records).data
        response = Response(serialized_data)
        return response

    @api_auth_token_required
    def post(self, request, provider_id, identity_id):
        """
        Create a new object based on DATA
        """
        pass


class MaintenanceRecord(APIView):
    """
    Represents:
        Calls to modify the single machine
    TODO: DELETE when we allow owners to 'end-date' their machine..
    """
    @api_auth_token_required
    def get(self, request, record_id):
        """
        Lookup the maintenance record information
        (Lookup using the given provider/identity)
        Update on server (If applicable)
        """
        try:
            mach_request = CoreMaintenanceRecord.objects.get(id=record_id)
        except CoreMaintenanceRecord.DoesNotExist:
            return Response(
                'No machine request with id %s' % machine_export_id,
                status=status.HTTP_404_NOT_FOUND)

        serialized_data = MaintenanceRecordSerializer(mach_request).data
        response = Response(serialized_data)
        return response

    @api_auth_token_required
    def patch(self, request, record_id):
        """
        Meta data changes in 'pending' are OK
        Status change 'pending' --> 'cancel' are OK
        All other changes should FAIL
        """
        #user = request.user
        data = request.DATA
        try:
            record =\
            CoreMaintenanceRecord.objects.get(id=record_id)
        except CoreMaintenanceRecord.DoesNotExist:
            return Response(
                'No machine request with id %s' % record_id,
                status=status.HTTP_404_NOT_FOUND)

        serializer = MaintenanceRecordSerializer(record, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @api_auth_token_required
    def put(self, request, record_id):
        """
        Meta data changes in 'pending' are OK
        Status change 'pending' --> 'cancel' are OK
        All other changes should FAIL
        """
        #user = request.user
        data = request.DATA
        try:
            record = CoreMaintenanceRecord.objects.get(id=record_id)
        except CoreMaintenanceRecord.DoesNotExist:
            return Response(
                'No maintenance record with id %s' % record_id,
                status=status.HTTP_404_NOT_FOUND)

        serializer = MaintenanceRecordSerializer(record,
                                             data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
