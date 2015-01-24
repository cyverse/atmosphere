"""
Atmosphere quota rest api.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.shortcuts import get_object_or_404

from api.permissions import ApiAuthRequired
from api.serializers import QuotaSerializer

from core.models import Quota


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
