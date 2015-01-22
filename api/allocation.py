"""
Atmosphere allocation rest api.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.shortcuts import get_object_or_404

from api import failure_response
from api.permissions import ApiAuthRequired
from api.serializers import AllocationSerializer, AllocationRequestSerializer

from core.models import Allocation, AllocationRequest, Identity,\
    IdentityMembership
from core.models.request import get_status_type


class AllocationList(APIView):
    """
    """
    permission_classes = (ApiAuthRequired,)

    def get(self, request):
        """
        """
        quotas = Allocation.objects.all()
        serialized_data = AllocationSerializer(quotas, many=True).data
        return Response(serialized_data)

    def post(self, request):
        """
        """
        data = request.DATA
        serializer = AllocationSerializer(data=data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AllocationDetail(APIView):
    """
    """
    permission_classes = (ApiAuthRequired,)

    def get(self, request, allocation_id):
        """
        """
        allocation = get_object_or_404(Allocation, id=allocation_id)
        serialized_data = AllocationSerializer(allocation).data
        return Response(serialized_data)

    def put(self, request, quota_id):
        """
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
        """
        data = request.DATA
        allocation = get_object_or_404(Allocation, id=quota_id)
        serializer = AllocationSerializer(allocation, data=data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AllocationRequestList(APIView):
    """
    """
    permission_classes = (ApiAuthRequired,)

    def get(self, request, provider_uuid, identity_uuid):
        try:
            identity = Identity.objects.get(uuid=identity_uuid)
            membership = IdentityMembership.objects.get(identity=identity)
        except Identity.DoesNotExist:
            return failure_response(status.HTTP_400_BAD_REQUEST,
                                    "Identity not found.")
        except IdentityMembership.DoesNotExist:
            return failure_response(status.HTTP_400_BAD_REQUEST,
                                    "IdentityMembership not found.")
        allocation_requests = AllocationRequest.objects.filter(
            membership=membership)
        serializer = AllocationRequestSerializer(allocation_requests,
                                                 many=True)
        return Response(serializer.data)

    def post(self, request, provider_uuid, identity_uuid):
        """
        """
        try:
            identity = Identity.objects.get(uuid=identity_uuid)
            membership = IdentityMembership.objects.get(identity=identity)
        except Identity.DoesNotExist:
            return failure_response(status.HTTP_400_BAD_REQUEST,
                                    "Identity not found.")
        except IdentityMembership.DoesNotExist:
            return failure_response(status.HTTP_400_BAD_REQUEST,
                                    "IdentityMembership not found.")

        data = request.DATA
        status_type = get_status_type()

        new_allocation = AllocationRequest(
            membership=membership, current_allocation=membership.allocation,
            status=status_type, created_by=request.user)

        serializer = AllocationRequestSerializer(new_allocation,
                                                 data=data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
