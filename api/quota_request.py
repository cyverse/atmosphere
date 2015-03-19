"""
Atmosphere quota request rest api.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.shortcuts import get_object_or_404

from api import failure_response
from api.permissions import ApiAuthRequired
from api.serializers import QuotaRequestSerializer

from core.models import Identity, IdentityMembership, QuotaRequest
from core.models.status_type import get_status_type


class QuotaRequestList(APIView):
    """
    Lists or Creates a QuotaRequest
    """
    permission_classes = (ApiAuthRequired,)

    def get(self, request, provider_uuid, identity_uuid):
        """
        Fetches all QuotaRequest for a specific identity
        """
        membership = None

        try:
            identity = Identity.objects.get(uuid=identity_uuid)
            membership = IdentityMembership.objects.get(identity=identity)
        except Identity.DoesNotExist:
            return failure_response(status.HTTP_400_BAD_REQUEST,
                                    "Identity not found.")
        except IdentityMembership.DoesNotExist:
            return failure_response(status.HTTP_400_BAD_REQUEST,
                                    "IdentityMembership not found.")

        quota_requests = QuotaRequest.objects.filter(membership=membership)
        serializer = QuotaRequestSerializer(quota_requests, many=True)
        return Response(serializer.data)

    def post(self, request, provider_uuid, identity_uuid):
        """
        Creates a new QuotaRequest for the specific
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

        # Determine if the user is a member of the identity
        if not membership.is_member(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)

        # Only allow 1 active request at a time
        if QuotaRequest.is_active(membership):
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                "An existing quota request is already open.")

        data = request.DATA
        status_type = get_status_type()

        new_quota = QuotaRequest(
            membership=membership, created_by=request.user, status=status_type)

        serializer = QuotaRequestSerializer(new_quota, data=data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class QuotaRequestDetail(APIView):
    """
    Fetches or updates a specific QuotaRequest
    """
    permission_classes = (ApiAuthRequired,)

    user_whitelist = ["description", "request"]

    admin_whitelist = ["end_date", "status", "description", "request",
                       "admin_message"]

    def get_object(self, identifier):
        return get_object_or_404(QuotaRequest, uuid=identifier)

    def get(self, request, provider_uuid, identity_uuid, quota_request_uuid):
        """
        Fetch the specified QuotaRequest
        """
        quota_request = self.get_object(quota_request_uuid)
        serialized_data = QuotaRequestSerializer(quota_request).data
        return Response(serialized_data)

    def put(self, request, provider_uuid, identity_uuid, quota_request_uuid):
        """
        Updates the QuotaRequest

        Users are only allowed to update description or request, all other
        fields will be ignored.

        A super user or staff user can end date or close out a request and
        provide an admin message.
        """
        data = request.DATA
        quota_request = self.get_object(quota_request_uuid)

        if not quota_request.can_modify(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)

        if request.user.is_staff or request.user.is_superuser:
            whitelist = QuotaRequestDetail.admin_whitelist
        else:
            whitelist = QuotaRequestDetail.user_whitelist

        #: Select fields that are in white list
        fields = {field: data[field] for field in whitelist if field in data}
        serializer = QuotaRequestSerializer(
            quota_request, data=fields, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, provider_uuid, identity_uuid, quota_request_uuid):
        """
        Partially update the QuotaRequest

        Users are only allowed to update description or request, all other
        fields will be ignored.

        A super user or staff user can end date or close out a request and
        provide an admin message.
        """
        data = request.DATA
        quota_request = self.get_object(quota_request_uuid)

        if not quota_request.can_modify(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)

        if request.user.is_staff or request.user.is_superuser:
            whitelist = QuotaRequestDetail.admin_whitelist
        else:
            whitelist = QuotaRequestDetail.user_whitelist

        #: Select fields that are in white list
        fields = {field: data[field] for field in whitelist if field in data}
        serializer = QuotaRequestSerializer(
            quota_request, data=fields, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, provider_uuid, identity_uuid,
               quota_request_uuid):
        """
        Deletes the QuotaRequest

        The request can be deleted by the owner when it still has a pending
        status.
        """
        quota_request = self.get_object(quota_request_uuid)

        # Check if the user own this request
        if quota_request.can_modify(request.user):
            quota_request.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)
