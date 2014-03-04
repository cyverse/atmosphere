"""
Atmosphere api Hypervisor.
"""

# atmosphere libraries
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response

from api import prepare_driver, invalid_creds
from core.models import Provider
from service.driver import get_admin_driver

from authentication.decorators import api_auth_token_required


class HypervisorList(APIView):
    """
    List all available Hypervisors
    """
    @api_auth_token_required
    def get(self, request, provider_id, identity_id):
        """
        Using provider and identity, getlist of machines
        TODO: Cache this request
        """
        #TODO: Decide how we should pass this in (I.E. GET query string?)
        active = False
        user = request.user
        provider = Provider.objects.filter(id=provider_id)
        if not provider:
            return invalid_creds(provider_id, identity_id)
        esh_driver = get_admin_driver(provider[0])
        esh_hypervisor_list = []
        if hasattr(esh_driver._connection, 'ex_list_hypervisor_nodes'):
            esh_hypervisor_list = esh_driver._connection.ex_list_hypervisor_nodes()
        region_name = esh_driver._connection._ex_force_service_region
        for obj in esh_hypervisor_list:
            obj['service_region'] = region_name
        response = Response(esh_hypervisor_list)
        return response


class HypervisorDetail(APIView):
    """
    View a single Hypervisor
    """
    @api_auth_token_required
    def get(self, request, provider_id, identity_id, hypervisor_id):
        """
        Lookup the Hypervisor information (Lookup using the given provider/identity)
        Update on server DB (If applicable)
        """
        user = request.user
        provider = Provider.objects.filter(id=provider_id)
        if not provider:
            return invalid_creds(provider_id, identity_id)
        esh_driver = get_admin_driver(provider[0])
        if not esh_driver:
            return invalid_creds(provider_id, identity_id)
        hypervisor = {}
        if hasattr(esh_driver._connection, 'ex_detail_hypervisor_node'):
            hypervisor = esh_driver._connection\
                    .ex_detail_hypervisor_node(hypervisor_id)
        response = Response(hypervisor)
        return response

