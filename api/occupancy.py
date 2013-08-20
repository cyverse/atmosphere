"""
atmosphere service provider occupancy rest api.

"""

from rest_framework.views import APIView
from rest_framework.response import Response

from authentication.decorators import api_auth_token_required

from core.models.identity import Identity
from core.models.size import convertEshSize

from api import get_esh_driver
from api.serializers import ProviderSizeSerializer


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
        driver = get_esh_driver(Identity.objects.filter(
            provider__id=provider_id)[0])
        meta_driver = driver.meta()
        esh_size_list  = meta_driver.occupancy()
        #Formatting..
        core_size_list = [convertEshSize(size, provider_id, None)
                          for size in esh_size_list]
        #return it
        serialized_data = ProviderSizeSerializer(core_size_list, many=True).data
        return Response(serialized_data)
