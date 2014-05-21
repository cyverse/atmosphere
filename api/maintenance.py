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

from api.serializers import MaintenanceRecordSerializer
from api.permissions import InMaintenance, ApiAuthRequired


class MaintenanceRecordList(APIView):
    """
    A list of all maintenance.
    Use ?active=True to get current maintenenace.
    """

    permission_classes = (ApiAuthRequired,)
    
    def get(self, request):
        """
        """
        user = request.user
        groups = user.group_set.all()
        providers = []
        records = CoreMaintenanceRecord.objects.none()
        for g in groups:
            for p in g.providers.all():
                if p not in providers:
                    providers.append(p)
        if 'active' in request.GET:
            if request.GET['active'].lower() == "true":
                now_time = timezone.now()
                for p in providers:
                    records |= CoreMaintenanceRecord.active(p)
            else:
                all_records = CoreMaintenanceRecord.objects.all()
                now_time = timezone.now()
                for p in providers:
                    records |= CoreMaintenanceRecord.active(p)
                records = all_records.exclude(id__in=records)
        else:
            records = CoreMaintenanceRecord.objects.filter(
                Q(provider__in=providers) | Q(provider=None))
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
