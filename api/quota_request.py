"""
Atmosphere quota request rest api.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.shortcuts import get_object_or_404

from api import failure_response
from api.permissions import ApiAuthRequired
from api.serializers import QuotaRequestSerializer, UserQuotaRequestSerializer

from core.exceptions import InvalidMembership, ProviderLimitExceeded
from core.models import Identity, IdentityMembership, QuotaRequest
from core.models.status_type import get_status_type


class QuotaRequestList(APIView):
    """
    Lists or Creates a QuotaRequest
    """
    permission_classes = (ApiAuthRequired,)

    def get_objects(self, request):
        memberships = []
        identities = request.user.identity_set.all()

        for identity in identities:
            memberships.extend(identity.identitymembership_set.all())

        if request.user.is_staff:
            quota_requests = QuotaRequest.objects.all()
        else:
            quota_requests = QuotaRequest.objects.filter(
                membership__in=memberships)

        return quota_requests

    def get(self, request):
        """
        Fetches all QuotaRequest for a specific identity
        """
        quota_requests = self.get_objects(request)
        serializer = QuotaRequestSerializer(quota_requests, many=True)
        return Response(serializer.data)

    def post(self, request):
        """
        Creates a new QuotaRequest for the specific
        """
        data = request.DATA
        data['created_by'] = request.user
        serializer = QuotaRequestSerializer(data=data)

        if not serializer.is_valid():
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            serializer.save()
        except ProviderLimitExceeded:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                "An existing quota request is already open.")
        except InvalidMembership:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                "Invalid membership provided for user.")

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class QuotaRequestDetail(APIView):
    """
    Fetches or updates a specific QuotaRequest
    """
    permission_classes = (ApiAuthRequired,)

    def get_object(self, identifier):
        return get_object_or_404(QuotaRequest, uuid=identifier)

    def get(self, request, quota_request_uuid):
        """
        Fetch the specified QuotaRequest
        """
        quota_request = self.get_object(quota_request_uuid)
        serialized_data = QuotaRequestSerializer(quota_request).data
        return Response(serialized_data)

    def put(self, request, quota_request_uuid):
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

        serializer = UserQuotaRequestSerializer(
            quota_request, data=data)

        if serializer.is_valid():
            quota_request = serializer.save()
            serialized_data = UserQuotaRequestSerializer(quota_request).data
            return Response(serialized_data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, quota_request_uuid):
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

        serializer = UserQuotaRequestSerializer(
            quota_request, data=data, partial=True)

        if serializer.is_valid():
            quota_request = serializer.save()
            serialized_data = QuotaRequestSerializer(quota_request).data
            return Response(serialized_data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, quota_request_uuid):
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
