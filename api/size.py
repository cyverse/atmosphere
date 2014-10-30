"""
Atmosphere api size.
"""

# atmosphere libraries
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response

from core.models.size import convert_esh_size

from service.driver import prepare_driver

from api import invalid_creds
from api.permissions import InMaintenance, ApiAuthRequired
from api.serializers import ProviderSizeSerializer




class SizeList(APIView):
    """List all active sizes."""
    permission_classes = (ApiAuthRequired,)
    
    def get(self, request, provider_id, identity_id):
        """
        Using provider and identity, getlist of machines
        TODO: Cache this request
        """
        #TODO: Decide how we should pass this in (I.E. GET query string?)
        active = False
        user = request.user
        esh_driver = prepare_driver(request, provider_id, identity_id)
        if not esh_driver:
            return invalid_creds(provider_id, identity_id)
        esh_size_list = esh_driver.list_sizes()
        all_size_list = [convert_esh_size(size, provider_id)
                         for size in esh_size_list]
        if active:
            all_size_list = [s for s in all_size_list if s.active()]
        serialized_data = ProviderSizeSerializer(all_size_list, many=True).data
        response = Response(serialized_data)
        return response


class Size(APIView):
    """View a single size"""
    permission_classes = (ApiAuthRequired,)
    
    def get(self, request, provider_id, identity_id, size_id):
        """
        Lookup the size information (Lookup using the given provider/identity)
        Update on server DB (If applicable)
        """
        user = request.user
        esh_driver = prepare_driver(request, provider_id, identity_id)
        if not esh_driver:
            return invalid_creds(provider_id, identity_id)
        core_size = convert_esh_size(esh_driver.get_size(size_id), provider_id)
        serialized_data = ProviderSizeSerializer(core_size).data
        response = Response(serialized_data)
        return response
