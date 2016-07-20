"""
Atmosphere api size.
"""
from django.utils import timezone

from rest_framework.response import Response
from rest_framework import status

from core.exceptions import ProviderNotActive
from core.models.size import convert_esh_size

from service.driver import prepare_driver
from rtwo.exceptions import LibcloudInvalidCredsError, LibcloudBadResponseError

from socket import error as socket_error
from rtwo.exceptions import ConnectionFailure

from api import invalid_creds, malformed_response, connection_failure
from api.exceptions import inactive_provider, failure_response
from api.v1.serializers import ProviderSizeSerializer
from api.v1.views.base import AuthAPIView


class SizeList(AuthAPIView):

    """
    List all active sizes.
    """

    def get(self, request, provider_uuid, identity_uuid):
        """
        Using provider and identity, getlist of machines
        TODO: Cache this request
        """
        # TODO: Decide how we should pass this in (I.E. GET query string?)
        active = False
        user = request.user
        try:
            esh_driver = prepare_driver(request, provider_uuid, identity_uuid)
        except ProviderNotActive as pna:
            return inactive_provider(pna)
        except Exception as e:
            return failure_response(
                status.HTTP_409_CONFLICT,
                e.message)

        if not esh_driver:
            return invalid_creds(provider_uuid, identity_uuid)
        try:
            esh_size_list = esh_driver.list_sizes()
        except LibcloudBadResponseError:
            return malformed_response(provider_uuid, identity_uuid)
        except LibcloudInvalidCredsError:
            return invalid_creds(provider_uuid, identity_uuid)
        except (socket_error, ConnectionFailure):
            return connection_failure(provider_uuid, identity_uuid)
        all_size_list = [convert_esh_size(size, provider_uuid)
                         for size in esh_size_list]
        if active:
            all_size_list = [s for s in all_size_list if s.active()]
        serialized_data = ProviderSizeSerializer(all_size_list, many=True).data
        response = Response(serialized_data)
        return response


class Size(AuthAPIView):

    """
    View a single size.
    """

    def get(self, request, provider_uuid, identity_uuid, size_id):
        """
        Lookup the size information (Lookup using the given provider/identity)
        Update on server DB (If applicable)
        """
        user = request.user
        try:
            esh_driver = prepare_driver(request, provider_uuid, identity_uuid)
        except ProviderNotActive as pna:
            return inactive_provider(pna)
        except Exception as e:
            return failure_response(
                status.HTTP_409_CONFLICT,
                e.message)

        if not esh_driver:
            return invalid_creds(provider_uuid, identity_uuid)
        core_size = convert_esh_size(
            esh_driver.get_size(size_id),
            provider_uuid)
        serialized_data = ProviderSizeSerializer(core_size).data
        response = Response(serialized_data)
        return response
