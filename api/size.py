"""
Atmosphere service size .
"""

# atmosphere libraries
from rest_framework.views import APIView
from rest_framework.response import Response

from authentication.decorators import api_auth_token_required

from core.models.size import convertEshSize

from api.serializers import ProviderSizeSerializer

from api import prepareDriver


class SizeList(APIView):
    """
    List all available sizes
    """
    @api_auth_token_required
    def get(self, request, provider_id, identity_id):
        """
        Using provider and identity, getlist of machines
        TODO: Cache this request
        """
        user = request.user
        esh_driver = prepareDriver(request, identity_id)
        esh_size_list = esh_driver.list_sizes()
        core_size_list = [convertEshSize(size, provider_id, user)
                          for size in esh_size_list]
        serialized_data = ProviderSizeSerializer(core_size_list, many=True).data
        response = Response(serialized_data)
        return response


class Size(APIView):
    """
    View a single size
    """
    @api_auth_token_required
    def get(self, request, provider_id, identity_id, size_id):
        """
        Lookup the size information (Lookup using the given provider/identity)
        Update on server DB (If applicable)
        """
        user = request.user
        esh_driver = prepareDriver(request, identity_id)
        eshSize = esh_driver.get_size(size_id)
        coreSize = convertEshSize(eshSize, provider_id, user)
        serialized_data = ProviderSizeSerializer(coreSize).data
        response = Response(serialized_data)
        return response
