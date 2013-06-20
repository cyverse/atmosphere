"""
atmosphere service provider rest api.

"""

from rest_framework.views import APIView
from rest_framework.response import Response

from authentication.decorators import api_auth_token_required

from core.models.group import Group

from api.serializers import ProviderSerializer


class ProviderList(APIView):
    """
    List of active providers
    """
    @api_auth_token_required
    def get(self, request):
        """
        List all providers accessible by request user
        """
        username = request.user.username
        group = Group.objects.get(name=username)
        providers = group.providers.filter(active=True,
                                           end_date=None).order_by('id')
        #providers = CoreProvider.objects.order_by('id')
        serialized_data = ProviderSerializer(providers, many=True).data
        return Response(serialized_data)


class Provider(APIView):
    """
    Show single provider
    """
    @api_auth_token_required
    def get(self, request, provider_id):
        """
        return provider if accessible by request user
        """
        username = request.user.username
        group = Group.objects.get(name=username)
        provider = group.providers.get(id=provider_id,
                                       active=True, end_date=None)

        serialized_data = ProviderSerializer(provider).data
        return Response(serialized_data)
