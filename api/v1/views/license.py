"""
Atmosphere License rest api.
"""
from django.shortcuts import get_object_or_404

from rest_framework.response import Response
from rest_framework import status

from core.models import License as CoreLicense

from api.v1.serializers import POST_LicenseSerializer, LicenseSerializer
from api.v1.views.base import AuthAPIView


class LicenseList(AuthAPIView):

    def get(self, request):
        user = request.user
        licenses = CoreLicense.objects.filter(created_by=user)
        serialized_data = LicenseSerializer(
            licenses, many=True,
            context={"request": request}).data
        return Response(serialized_data)

    def post(self, request):
        data = request.data
        data['created_by'] = request.user
        serializer = POST_LicenseSerializer(
            data=data,
            context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class License(AuthAPIView):

    def get(self, request, license_id):
        license = get_object_or_404(CoreLicense, id=license_id)
        serialized_data = LicenseSerializer(
            license,
            context={"request": request}).data
        return Response(serialized_data)

    def put(self, request, license_id):
        return self._update_license(request, license_id)

    def patch(self, request, license_id):
        return self._update_license(request, license_id, partial=True)

    def _update_license(self, request, license_id, partial=False):
        data = request.data
        license = get_object_or_404(CoreLicense, id=license_id)
        serializer = LicenseSerializer(
            license, context={"request": request},
            data=data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
