"""
Atmosphere allocation rest api.
"""
from django.shortcuts import get_object_or_404

from rest_framework.response import Response
from rest_framework import status

from core.models import Allocation, AllocationStrategy
from core.query import only_active_memberships

from api.v1.serializers import AllocationSerializer, AllocationResultSerializer
from api.v1.views.base import AuthAPIView


class AllocationList(AuthAPIView):

    """
    Lists or creates new Allocations
    """

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
        data = request.data
        serializer = AllocationSerializer(data=data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AllocationDetail(AuthAPIView):

    """
    Fetches or updates an Allocation
    """

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
        data = request.data
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
        data = request.data
        allocation = get_object_or_404(Allocation, id=quota_id)
        serializer = AllocationSerializer(allocation, data=data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MonitoringList(AuthAPIView):

    """
    Runs the allocation engine and returns detailed monitoring information
    """

    def get(self, request):
        """
        Fetch the specified Allocation
        """
        user = request.user
        allocation_results = []
        memberships = only_active_memberships(user)
        for membership in memberships:
            strat = AllocationStrategy.objects.get(
                provider=membership.identity.provider)
            allocation_result = strat.execute(
                membership.identity, membership.allocation)
            allocation_results.append(allocation_result)
        serialized_data = AllocationResultSerializer(
            allocation_results, many=True).data
        return Response(serialized_data)
