"""
Atmosphere quota rest api.
"""
from rest_framework.response import Response
from rest_framework import status

from django.shortcuts import get_object_or_404

from api.v1.serializers import QuotaSerializer
from api.v1.views.base import AuthAPIView

from core.models import Quota


class QuotaList(AuthAPIView):

    """
    Lists or creates new Quotas
    """

    def get(self, request):
        """
        Returns a list of all existing Quotas
        """
        quotas = Quota.objects.all()
        serialized_data = QuotaSerializer(quotas, many=True).data
        return Response(serialized_data)

    def post(self, request):
        """
        Creates a new Quota
        """
        data = request.data
        serializer = QuotaSerializer(data=data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class QuotaDetail(AuthAPIView):

    """
    Fetches or updates a Quota
    """

    def get(self, request, quota_id):
        """
        Return the specified Quota
        """
        quota = get_object_or_404(Quota, id=quota_id)
        serialized_data = QuotaSerializer(quota).data
        return Response(serialized_data)

    def put(self, request, quota_id):
        """
        Updates the specified Quota
        """
        data = request.data
        quota = get_object_or_404(Quota, id=quota_id)
        serializer = QuotaSerializer(quota, data=data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, quota_id):
        """
        Partially updates the specified Quota
        """
        data = request.data
        quota = get_object_or_404(Quota, id=quota_id)
        serializer = QuotaSerializer(quota, data=data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
