"""
Atmosphere api flow.
"""
from rest_framework.views import APIView
from rest_framework.response import Response


from core.models.size import convert_esh_size

from api.serializers import ProviderSizeSerializer

from api import invalid_creds
from api.permissions import InMaintenance, ApiAuthRequired
from service.driver import prepare_driver


class FlowList(APIView):
    """
    List all active flows for a provider and identity.
    """
    permission_classes = (ApiAuthRequired,)

    def get(self, request, provider_uuid, identity_uuid):
        """
        """
        user = request.user
        esh_driver = prepare_driver(request, provider_uuid, identity_uuid)
        if not esh_driver:
            return invalid_creds(provider_uuid, identity_uuid)
        serialized_data = []
        response = Response(serialized_data)
        return response


class Flow(APIView):
    """
    View details on a flow.
    """
    permission_classes = (ApiAuthRequired,)

    def get(self, request, provider_uuid, identity_uuid, flow_id):
        """
        """
        user = request.user
        esh_driver = prepare_driver(request, provider_uuid, identity_uuid)
        if not esh_driver:
            return invalid_creds(provider_uuid, identity_uuid)
        esh_size = []
        serialized_data = []
        response = Response(serialized_data)
        return response
