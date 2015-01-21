"""
Atmosphere quota rest api.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.shortcuts import get_object_or_404

from api import failure_response
from api.permissions import ApiAuthRequired
from api.serializers import QuotaSerializer, QuotaRequestSerializer

from core.models import Identity, IdentityMembership, Quota, QuotaRequest
from core.models.request import get_status_type


class QuotaList(APIView):
    """
    """
    permission_classes = (ApiAuthRequired,)

    def get(self, request):
        """
        """
        quotas = Quota.objects.all()
        serialized_data = QuotaSerializer(quotas, many=True).data
        return Response(serialized_data)

    def post(self, request):
        """
        """
        data = request.DATA
        serializer = QuotaSerializer(data=data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class QuotaDetail(APIView):
    """
    """
    permission_classes = (ApiAuthRequired,)

    def get(self, request, quota_id):
        """
        """
        quota = get_object_or_404(Quota, id=quota_id)
        serialized_data = QuotaSerializer(quota).data
        return Response(serialized_data)

    def put(self, request, quota_id):
        """
        """
        data = request.DATA
        quota = get_object_or_404(Quota, id=quota_id)
        serializer = QuotaSerializer(quota, data=data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, quota_id):
        """
        """
        data = request.DATA
        quota = get_object_or_404(Quota, id=quota_id)
        serializer = QuotaSerializer(quota, data=data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class QuotaRequestList(APIView):
    """
    """
    permission_classes = (ApiAuthRequired,)

    def get(self, request, provider_uuid, identity_uuid):
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

        new_quota = QuotaRequest(
            membership=membership, current_quota=membership.quota,
            status=status_type, created_by=request.user)

        serializer = QuotaRequestSerializer(new_quota, data=data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class QuotaRequestDetail(APIView):
    """
    """
    permission_classes = (ApiAuthRequired,)

    def get_object(self, identifier):
        return get_object_or_404(QuotaRequest, uuid=identifier)

    def get(self, request, provider_uuid, identity_uuid, quota_request_uuid):
        """
        """
        quota_request = self.get_object(quota_request_uuid)
        serialized_data = QuotaRequestSerializer(quota_request).data
        return Response(serialized_data)

    def put(self, request, provider_uuid, identity_uuid, quota_request_uuid):
        """
        """
        data = request.data
        quota_request = self.get_object(quota_request_uuid)
        serializer = QuotaRequestSerializer(quota_request, data=data)

        if serializer.is_valid():
            status = data["status"]
            self.check_status_and_update(serializer.validated_data)
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, provider_uuid, identity_uuid, quota_request_uuid):
        """
        """
        data = request.DATA
        quota_request = self.get_object(quota_request_uuid)
        serializer = QuotaRequestSerializer(
            quota_request, data=data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
