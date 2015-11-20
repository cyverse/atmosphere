"""
atmosphere service provider occupancy rest api.

"""
from django.utils import timezone

from socket import error as socket_error
from rtwo.exceptions import ConnectionFailure

from rest_framework import status
from rest_framework.response import Response

from core.models.provider import Provider
from core.models.size import convert_esh_size

from service.driver import get_admin_driver

from api import failure_response
from api import connection_failure
from api.v1.serializers import ProviderSizeSerializer
from api.v1.views.base import AuthAPIView


class Occupancy(AuthAPIView):

    """
    Returns occupancy data for the specific provider.
    """

    def get(self, request, provider_uuid):
        """
        Returns occupancy data for the specific provider.
        """
        try:
            provider = Provider.get_active(provider_uuid)
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
        core_size_list = [convert_esh_size(size, provider_uuid)
                          for size in esh_size_list]
        serialized_data = ProviderSizeSerializer(core_size_list,
                                                 many=True).data
        return Response(serialized_data)


class Hypervisor(AuthAPIView):

    """
    Returns hypervisor statistics for the specific provider.
    """

    def get(self, request, provider_uuid):
        try:
            provider = Provider.get_active(provider_uuid)
        except Provider.DoesNotExist:
            return failure_response(
                status.HTTP_404_NOT_FOUND,
                "The provider does not exist.")
        admin_driver = get_admin_driver(provider)
        if not admin_driver:
            return failure_response(
                status.HTTP_404_NOT_FOUND,
                "The driver cannot be retrieved for this provider.")
        if not hasattr(admin_driver._connection, "ex_hypervisor_statistics"):
            return failure_response(
                status.HTTP_404_NOT_FOUND,
                "Occupancy statistics cannot be retrieved for this provider.")
        try:
            stats = admin_driver._connection.ex_hypervisor_statistics()
            return Response(stats)
        except (socket_error, ConnectionFailure):
            return connection_failure(provider_uuid)
        except Exception as exc:
            return failure_response(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "Error occurred while retrieving statistics: %s" %
                exc)
