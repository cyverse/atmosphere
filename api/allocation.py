"""
Atmosphere allocation rest api.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.shortcuts import get_object_or_404

from api.permissions import ApiAuthRequired
from api.serializers import AllocationSerializer

from core.models import Allocation


class AllocationList(APIView):
    """
    Lists or creates new Allocations
    """
    permission_classes = (ApiAuthRequired,)

    def get(self, request):
        """
        Returns a list of all existing Allocations
        """
        quotas = Allocation.objects.all()
        serialized_data = AllocationSerializer(quotas, many=True).data
        return Response(serialized_data)

    def post(self, request):
        """
        Creates a new Allocation
        """
        data = request.DATA
        serializer = AllocationSerializer(data=data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AllocationDetail(APIView):
    """
    Fetches or updates an Allocation
    """
    permission_classes = (ApiAuthRequired,)

    def get(self, request, allocation_id):
        """
        Fetch the specified Allocation
        """
        allocation = get_object_or_404(Allocation, id=allocation_id)
        serialized_data = AllocationSerializer(allocation).data
        return Response(serialized_data)

    def put(self, request, quota_id):
        """
        Updates the specified Allocation
        """
        data = request.DATA
        allocation = get_object_or_404(Allocation, id=quota_id)
        serializer = AllocationSerializer(allocation, data=data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, quota_id):
        """
        Partially updates the specified Allocation
        """
        data = request.DATA
        allocation = get_object_or_404(Allocation, id=quota_id)
        serializer = AllocationSerializer(allocation, data=data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
