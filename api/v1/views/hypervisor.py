import json

from django.utils import timezone

from rest_framework.response import Response

from socket import error as socket_error
from rtwo.exceptions import ConnectionFailure
from rest_framework import status

from core.models import Provider

from service.driver import get_admin_driver

from api import invalid_creds, connection_failure, failure_response
from api.v1.views.base import AuthAPIView


class HypervisorList(AuthAPIView):

    """
    List all available Hypervisors
    """

    def get(self, request, provider_uuid, identity_uuid):
        """
        Using provider and identity, getlist of machines
        TODO: Cache this request
        """
        # TODO: Decide how we should pass this in (I.E. GET query string?)
        active = False
        user = request.user
        provider = Provider.objects.filter(uuid=provider_uuid)
        if not provider:
            return invalid_creds(provider_uuid, identity_uuid)
        esh_driver = get_admin_driver(provider[0])
        esh_hypervisor_list = []
        if not hasattr(esh_driver._connection, 'ex_list_hypervisor_nodes'):
            return failure_response(
                status.HTTP_404_NOT_FOUND,
                "The Hypervisor List cannot be retrieved for this provider.")
        try:
            esh_hypervisor_list =\
                esh_driver._connection.ex_list_hypervisor_nodes()
            region_name = esh_driver._connection._ex_force_service_region
            for obj in esh_hypervisor_list:
                obj['service_region'] = region_name

            response = Response(esh_hypervisor_list)
            return response
        except (socket_error, ConnectionFailure):
            return connection_failure(provider_uuid, identity_uuid)
        except Exception as exc:
            return failure_response(
                status.HTTP_404_NOT_FOUND,
                "Error encountered retrieving hypervisor list:%s" % exc)


class HypervisorDetail(AuthAPIView):

    """
    View a single Hypervisor
    """

    def get(self, request, provider_uuid, identity_uuid, hypervisor_id):
        """
        Lookup the Hypervisor information (Lookup using the given
        provider/identity)
        Update on server DB (If applicable)
        """
        user = request.user
        provider = Provider.objects.filter(uuid=provider_uuid)
        if not provider:
            return invalid_creds(provider_uuid, identity_uuid)
        esh_driver = get_admin_driver(provider[0])
        if not esh_driver:
            return invalid_creds(provider_uuid, identity_uuid)
        hypervisor = {}
        if not hasattr(esh_driver._connection, 'ex_detail_hypervisor_node'):
            return failure_response(
                status.HTTP_404_NOT_FOUND,
                "Hypervisor Details cannot be retrieved for this provider.")
        try:
            hypervisor = esh_driver._connection\
                .ex_detail_hypervisor_node(hypervisor_id)
            hypervisor['cpu_info'] = json.loads(hypervisor['cpu_info'])
            response = Response(hypervisor)
            return response
        except (socket_error, ConnectionFailure):
            return connection_failure(provider_uuid, identity_uuid)
        except Exception as exc:
            return failure_response(
                status.HTTP_404_NOT_FOUND,
                "Error encountered retrieving hypervisor details:%s" % exc)
