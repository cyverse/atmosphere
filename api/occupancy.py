"""
atmosphere service provider occupancy rest api.

"""
from django.utils import timezone

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response


from core.models.provider import Provider
from core.models.size import convert_esh_size

from service.driver import get_esh_driver, get_admin_driver

from api import failure_response
from api.permissions import InMaintenance, ApiAuthRequired
from api.serializers import ProviderSizeSerializer


class Occupancy(APIView):
    """Returns occupancy data for the specific provider."""
    permission_classes = (ApiAuthRequired,)
    
    def get(self, request, provider_id):
        """
        Returns occupancy data for the specific provider.
        """
        #Get meta for provider to call occupancy
        try:
            provider = Provider.get_active(provider_id)
        except Provider.DoesNotExist:
            return failure_response(
                status.HTTP_404_NOT_FOUND,
                "The provider does not exist.")
        admin_driver = get_admin_driver(provider)
        if not admin_driver:
            return failure_response(
                status.HTTP_404_NOT_FOUND,
                "The driver cannot be retrieved for this provider.")
        meta_driver = admin_driver.meta(admin_driver=admin_driver)
        esh_size_list = meta_driver.occupancy()
        core_size_list = [convert_esh_size(size, provider_id)
                          for size in esh_size_list]
        serialized_data = ProviderSizeSerializer(core_size_list,
                                                 many=True).data
        return Response(serialized_data)


class Hypervisor(APIView):
    """Returns hypervisor statistics for the specific provider.
    """
    permission_classes = (ApiAuthRequired,)
    
    def get(self, request, provider_id):
        try:
            provider = Provider.get_active(provider_id)
        except Provider.DoesNotExist:
            return failure_response(
                status.HTTP_404_NOT_FOUND,
                "The provider does not exist.")
        admin_driver = get_admin_driver(provider)
        if not admin_driver:
            return failure_response(
                status.HTTP_404_NOT_FOUND,
                "The driver cannot be retrieved for this provider.")
        if hasattr(admin_driver._connection, "ex_hypervisor_statistics"):
            return Response(
                admin_driver._connection.ex_hypervisor_statistics())
        else:
            return failure_response(
                status.HTTP_404_NOT_FOUND,
                "Hypervisor statistics are unavailable for this provider.")
