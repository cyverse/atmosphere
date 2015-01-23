"""
Atmosphere allocation request rest api.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.shortcuts import get_object_or_404

from api.permissions import ApiAuthRequired
from api.serializers import AllocationRequestSerializer

from core.models import AllocationRequest


class AllocationRequestDetail(APIView):
    """
    """
    permission_classes = (ApiAuthRequired,)

    user_whitelist = ["description", "request"]

    admin_whitelist = ["end_date", "status", "description", "request",
                       "admin_message"]

    def get_object(self, identifier):
        return get_object_or_404(AllocationRequest, uuid=identifier)

    def get(self, request, provider_uuid, identity_uuid, allocation_request_uuid):
        """
        """
        allocation_request = self.get_object(allocation_request_uuid)
        serialized_data = AllocationRequestSerializer(allocation_request).data
        return Response(serialized_data)

    def put(self, request, provider_uuid, identity_uuid, allocation_request_uuid):
        """
        """
        data = request.DATA
        allocation_request = self.get_object(allocation_request_uuid)

        if request.user.is_staff or request.user.is_superuser:
            whitelist = AllocationRequestDetail.admin_whitelist
        else:
            whitelist = AllocationRequestDetail.user_whitelist

        #: Select fields that are in white list
        fields = {field: data[field] for field in whitelist if field in data}
        serializer = AllocationRequestSerializer(
            allocation_request, data=fields, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, provider_uuid, identity_uuid, allocation_request_uuid):
        """
        """
        data = request.DATA
        allocation_request = self.get_object(allocation_request_uuid)

        if request.user.is_staff or request.user.is_superuser:
            whitelist = AllocationRequestDetail.admin_whitelist
        else:
            whitelist = AllocationRequestDetail.user_whitelist

        #: Select fields that are in white list
        fields = {field: data[field] for field in whitelist if field in data}
        serializer = AllocationRequestSerializer(
            allocation_request, data=fields, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
