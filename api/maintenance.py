"""
Atmosphere service maintenance record rest api.
"""
import copy

from django.db.models import Q
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from threepio import logger

from core.models.maintenance import MaintenanceRecord as CoreMaintenanceRecord
from core.models.provider import Provider

from api.serializers import MaintenanceRecordSerializer
from api.permissions import InMaintenance, ApiAuthRequired, ApiAuthOptional
from django.contrib.auth.models import AnonymousUser


class MaintenanceRecordList(APIView):
    """
    A list of all maintenance.
    Use ?active=True to get current maintenenace.
    """

    permission_classes = (ApiAuthOptional,)
    
    def get(self, request):
        """
        """
        query = request.GET
        user = request.user
        providers = []
        records = CoreMaintenanceRecord.objects.none()
        active_records = query.get('active','false').lower() == "true"
        if user and type(user) != AnonymousUser:
            groups = user.group_set.all()
            for g in groups:
                for p in g.providers.all():
                    if active_records:
                        records |= CoreMaintenanceRecord.active(p)
                    else:
                        records |= CoreMaintenanceRecord.objects.filter(
                                provider=p)
        if active_records:
            global_records = CoreMaintenanceRecord.active()
        else:
            global_records  = CoreMaintenanceRecord.objects.filter(
                    provider=None)
        records |= global_records
        return Response(MaintenanceRecordSerializer(records, many=True).data)


class MaintenanceRecord(APIView):
    """
    Represents a maintenance record.
    """
    permission_classes = (ApiAuthRequired,)
    
    def get(self, request, record_id):
        """
        Get a maintenance record.
        """
        try:
            mach_request = CoreMaintenanceRecord.objects.get(id=record_id)
        except CoreMaintenanceRecord.DoesNotExist:
            return Response('No maintenance record with id %s' % record_id,
                            status=status.HTTP_404_NOT_FOUND)
        return Response(MaintenanceRecordSerializer(mach_request).data)

    def patch(self, request, record_id):
        """
        Update a maintenance record.
        """
        #user = request.user
        data = request.DATA
        try:
            record = CoreMaintenanceRecord.objects.get(id=record_id)
        except CoreMaintenanceRecord.DoesNotExist:
            return Response('No maintenance record with id %s' % record_id,
                            status=status.HTTP_404_NOT_FOUND)

        serializer = MaintenanceRecordSerializer(record, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, record_id):
        """
        Update a maintenance record.
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
