"""
Atmosphere quota rest api.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from api import failure_response
from api.permissions import ApiAuthRequired
from api.serializers import QuotaSerializer

from core.models import Identity, IdentityMembership, Quota


class QuotaMembership(APIView):
    permission_classes = (ApiAuthRequired,)

    def get(self, request, provider_uuid, identity_uuid):
        """
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

        serialized_data = QuotaSerializer(membership.quota).data
        return Response(serialized_data)

    def put(self, request, provider_uuid, identity_uuid):
        """
        """
        data = request.DATA
        membership = None
        serializer = QuotaSerializer(data=data)

        try:
            identity = Identity.objects.get(uuid=identity_uuid)
            membership = IdentityMembership.objects.get(identity=identity)
        except Identity.DoesNotExist:
            return failure_response(status.HTTP_400_BAD_REQUEST,
                                    "Identity not found.")
        except IdentityMembership.DoesNotExist:
            return failure_response(status.HTTP_400_BAD_REQUEST,
                                    "IdentityMembership not found.")

        if not serializer.is_valid():
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)

        # Create or fetch quota
        fields = serializer.data
        (quota, created) = Quota.objects.get_or_create(**fields)

        # Update memberships quota
        membership.quota = quota
        membership.save()

        if created:
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, provider_uuid, identity_uuid):
        """
        """
        data = request.DATA
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

        serializer = QuotaSerializer(membership.quota, data=data, partial=True)

        if not serializer.is_valid():
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)

        # Create or fetch quota
        fields = serializer.data
        (quota, created) = Quota.objects.get_or_create(**fields)

        # Update memberships quota
        membership.quota = quota
        membership.save()

        if created:
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.data, status=status.HTTP_200_OK)


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
