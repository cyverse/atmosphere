"""
Atmosphere allocation rest api.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.shortcuts import get_object_or_404

from api import failure_response
from api.permissions import ApiAuthRequired
from api.serializers import AllocationSerializer

from core.models import Allocation, Identity, IdentityMembership


class AllocationMembership(APIView):
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

        serialized_data = AllocationSerializer(membership.allocation).data
        return Response(serialized_data)

    def put(self, request, provider_uuid, identity_uuid):
        """
        """
        data = request.DATA
        membership = None
        serializer = AllocationSerializer(data=data)

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

        # Create or fetch allocation
        fields = serializer.data
        (allocation, created) = Allocation.objetcs.get_or_create(**fields)

        # Update memberships allocation
        membership.allocation = serializer.object
        membership.save()

        if created:
            return Response(serializer.data, status=status.HTTP_200_CREATED)
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

        serializer = AllocationSerializer(membership.allocation,
                                          data=data, partial=True)

        if not serializer.is_valid():
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)

        # Create or fetch allocation
        fields = serializer.data
        (allocation, created) = Allocation.objetcs.get_or_create(**fields)

        # Update memberships allocation
        membership.allocation = serializer.object
        membership.save()

        if created:
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.data, status=status.HTTP_200_OK)
