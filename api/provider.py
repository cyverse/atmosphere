"""
atmosphere service provider rest api.

"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response


from core.models.group import Group
from core.models.provider import Provider as CoreProvider

from api import failure_response
from api.serializers import ProviderSerializer
from api.permissions import InMaintenance, ApiAuthRequired, CloudAdminUpdatingRequired


class ProviderList(APIView):
    """Providers represent the different Cloud configurations hosted on Atmosphere.
    Providers can be of type AWS, Eucalyptus, OpenStack.
    """
    permission_classes = (ApiAuthRequired,)
    
    def get(self, request):
        """
        Authentication Required, list of Providers on your account.
        """
        username = request.user.username
        group = Group.objects.get(name=username)
        try:
            providers = group.providers.filter(active=True,
                                               end_date=None).order_by('id')
        except CoreProvider.DoesNotExist:
            return failure_response(
                status.HTTP_404_NOT_FOUND,
                "The provider does not exist.")
        serialized_data = ProviderSerializer(providers, many=True).data
        return Response(serialized_data)


class Provider(APIView):
    """Providers represent the different Cloud configurations hosted on Atmosphere.
    Providers can be of type AWS, Eucalyptus, OpenStack.
    """
    permission_classes = (ApiAuthRequired, CloudAdminUpdatingRequired)

    def get(self, request, provider_uuid):
        """
        Authentication Required, return specific provider.
        """
        username = request.user.username
        group = Group.objects.get(name=username)
        try:
            provider = group.providers.get(uuid=provider_uuid,
                                           active=True, end_date=None)
        except CoreProvider.DoesNotExist:
            return failure_response(
                status.HTTP_404_NOT_FOUND,
                "The provider does not exist.")
        serialized_data = ProviderSerializer(provider).data
        return Response(serialized_data)

    def patch(self, request, provider_uuid):
        user = request.user
        data = request.DATA
        try:
            provider = CoreProvider.objects.get(
                cloudadministrator__user=user,
                uuid=provider_uuid)
        except CoreProvider.DoesNotExist:
            return failure_response(
                status.HTTP_404_NOT_FOUND,
                "The provider does not exist.")
        serializer = ProviderSerializer(provider, data=data,
                                        partial=True)

        if not serializer.is_valid():
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.data)
