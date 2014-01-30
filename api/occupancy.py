"""
atmosphere service provider occupancy rest api.

"""

from rest_framework.views import APIView
from rest_framework.response import Response

from authentication.decorators import api_auth_token_required

from core.models.provider import Provider
from core.models.size import convert_esh_size

from api import get_esh_driver
from api.serializers import ProviderSizeSerializer

from service.driver import get_admin_driver


class Occupancy(APIView):
    """
    Show single provider
    """
    @api_auth_token_required
    def get(self, request, provider_id):
        """
        return occupancy data for the specific provider
        """
        #Get meta for provider to call occupancy
        provider = Provider.objects.get(id=provider_id)
        admin_driver = get_admin_driver(provider)
        meta_driver = admin_driver.meta(admin_driver=admin_driver)
        esh_size_list = meta_driver.occupancy()
        #Formatting..
        core_size_list = [convert_esh_size(size, provider_id)
                          for size in esh_size_list]
        #return it
        serialized_data = ProviderSizeSerializer(core_size_list,
                                                 many=True).data
        return Response(serialized_data)
