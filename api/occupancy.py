"""
atmosphere service provider occupancy rest api.

"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from authentication.decorators import api_auth_token_required

from core.models.provider import Provider
from core.models.size import convert_esh_size

from api import failureJSON, get_esh_driver
from api.serializers import ProviderSizeSerializer

from service.driver import get_admin_driver


class Occupancy(APIView):
    """
    Show single provider
    """
    @api_auth_token_required
    def get(self, request, provider_id):
        """
        Returns occupancy data for the specific provider.
        """
        #Get meta for provider to call occupancy
        try:
            provider = Provider.objects.get(id=provider_id)
        except Provider.DoesNotExist:
            errorObj = failureJSON([{
                'code': 404,
                'message':
                'The provider does not exist.'}])
            return Response(errorObj, status=status.HTTP_404_NOT_FOUND)
        admin_driver = get_admin_driver(provider)
        meta_driver = admin_driver.meta(admin_driver=admin_driver)
        esh_size_list = meta_driver.occupancy()
        core_size_list = [convert_esh_size(size, provider_id)
                          for size in esh_size_list]
        serialized_data = ProviderSizeSerializer(core_size_list,
                                                 many=True).data
        return Response(serialized_data)


class Hypervisor(APIView):
    """
    Returns hypervisor statistics for the specific provider.
    """
    @api_auth_token_required
    def get(self, request, provider_id):
        try:
            provider = Provider.objects.get(id=provider_id)
        except Provider.DoesNotExist:
            errorObj = failureJSON([{
                'code': 404,
                'message':
                'The provider does not exist.'}])
            return Response(errorObj, status=status.HTTP_404_NOT_FOUND)
        admin_driver = get_admin_driver(provider)
        if hasattr(admin_driver._connection, "ex_hypervisor_statistics"):
            return Response(admin_driver._connection.ex_hypervisor_statistics())
        else:
            errorObj = failureJSON([{
                'code': 404,
                'message':
                'The provider does not exist.'}])
            return Response(errorObj, status=status.HTTP_404_NOT_FOUND)
