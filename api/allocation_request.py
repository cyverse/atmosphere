"""
Atmosphere allocation request rest api.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.shortcuts import get_object_or_404

from api import failure_response
from api.permissions import ApiAuthRequired
from api.serializers import AllocationRequestSerializer

from core.models import AllocationRequest, Identity, IdentityMembership
from core.models.status_type import get_status_type


class AllocationRequestList(APIView):
    """
    Lists or Creates a AllocationRequest
    """
    permission_classes = (ApiAuthRequired,)

    def get(self, request, provider_uuid, identity_uuid):
        """
        Fetches all AllocationRequests for a specific identity
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
        allocation_requests = AllocationRequest.objects.filter(
            membership=membership)
        serializer = AllocationRequestSerializer(allocation_requests,
                                                 many=True)
        return Response(serializer.data)

    def post(self, request, provider_uuid, identity_uuid):
        """
        Creates a new AllocationRequest for a specific identity
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
            membership=membership, created_by=request.user, status=status_type)

        serializer = AllocationRequestSerializer(new_allocation,
                                                 data=data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AllocationRequestDetail(APIView):
    """
    Fetches or updates a specific AllocatinRequest
    """
    permission_classes = (ApiAuthRequired,)

    user_whitelist = ["description", "request"]

    admin_whitelist = ["end_date", "status", "description", "request",
                       "admin_message"]

    def get_object(self, identifier):
        return get_object_or_404(AllocationRequest, uuid=identifier)

    def get(self, request, provider_uuid, identity_uuid,
            allocation_request_uuid):
        """
        Returns an AllocationRequest with the matching uuid
        """
        allocation_request = self.get_object(allocation_request_uuid)
        serialized_data = AllocationRequestSerializer(allocation_request).data
        return Response(serialized_data)

    def put(self, request, provider_uuid, identity_uuid,
            allocation_request_uuid):
        """
        Updates the AllocationRequest

        Users are only allowed to update description or request, all other
        fields will be ignored.

        A super user or staff user can end date or close out a request and
        provide an admin message.
        """
        data = request.DATA
        allocation_request = self.get_object(allocation_request_uuid)

        if not allocation_request.can_modify(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)

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

    def patch(self, request, provider_uuid, identity_uuid,
              allocation_request_uuid):
        """
        Paritally update the AllocationRequest

        Users are only allowed to update description or request, all other
        fields will be ignored.

        A super user or staff user can end date or close out a request and
        provide an admin message.
        """
        data = request.DATA
        allocation_request = self.get_object(allocation_request_uuid)

        if not allocation_request.can_modify(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)

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

    def delete(self, request, provider_uuid, identity_uuid,
               allocation_request_uuid):
        """
        Deletes the AllocationRequest

        The request can be deleted by the owner when it still has a pending
        status.
        """
        allocation_request = self.get_object(allocation_request_uuid)

        # Check if the user own this request
        if allocation_request.can_modify(request.user):
            allocation_request.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)
