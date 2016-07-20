"""
Atmosphere service machine rest api.

"""
import os

from django.core.paginator import Paginator,\
    PageNotAnInteger, EmptyPage
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework import status

from rtwo.exceptions import LibcloudInvalidCredsError, LibcloudBadResponseError
from socket import error as socket_error

from rtwo.exceptions import ConnectionFailure
from threepio import logger

from core.exceptions import ProviderNotActive
from core.models.license import License
from core.models.identity import Identity
from core.models.machine import compare_core_machines, filter_core_machine,\
    update_application_owner, convert_esh_machine, ProviderMachine

from service.driver import prepare_driver
from service.machine import update_machine_metadata
from service.search import search, CoreSearchProvider

from api.exceptions import (
    invalid_creds, malformed_response, connection_failure,
    failure_response, inactive_provider, invalid_provider_identity)
from api.pagination import OptionalPagination
from api.renderers import JPEGRenderer, PNGRenderer
from api.v1.serializers import ProviderMachineSerializer,\
    LicenseSerializer
from api.v1.views.base import AuthAPIView, AuthListAPIView


def provider_filtered_machines(request, provider_uuid,
                               identity_uuid, request_user=None):
    """
    Return all filtered machines. Uses the most common,
    default filtering method.
    """
    identity = Identity.objects.filter(uuid=identity_uuid)
    if not identity:
        raise ObjectDoesNotExist()

    try:
        esh_driver = prepare_driver(request, provider_uuid, identity_uuid)
    except Exception:
        # TODO: Observe the change of 'Fail loudly' here
        # and clean up the noise, rather than hide it.
        logger.exception(
            "Driver could not be prepared - Provider: %s , Identity: %s"
            % (provider_uuid, identity_uuid))
        esh_driver = None

    if not esh_driver:
        raise LibcloudInvalidCredsError()

    logger.debug(esh_driver)

    return list_filtered_machines(esh_driver, provider_uuid, request_user)


def list_filtered_machines(esh_driver, provider_uuid, request_user=None):
    esh_machine_list = esh_driver.list_machines()
    # TODO: I hate this. Make this black_list on
    # MACHINE TYPE ari/aki/eri/eki instead. - SG
    esh_machine_list = esh_driver.filter_machines(
        esh_machine_list,
        black_list=['eki-', 'eri-', 'aki-', 'ari-'])
    core_machine_list = [convert_esh_machine(esh_driver, mach,
                                             provider_uuid, request_user)
                         for mach in esh_machine_list]
    filtered_machine_list = [core_mach for core_mach in core_machine_list
                             if filter_core_machine(core_mach)]
    sorted_machine_list = sorted(filtered_machine_list,
                                 cmp=compare_core_machines)
    return sorted_machine_list


class MachineList(AuthAPIView):

    """
    List of machines.
    """

    def get(self, request, provider_uuid, identity_uuid):
        """
        Using provider and identity, getlist of machines
        TODO: Cache this request
        """
        try:
            request_user = request.user
            logger.debug("filtered_machine_list")
            filtered_machine_list = provider_filtered_machines(request,
                                                               provider_uuid,
                                                               identity_uuid,
                                                               request_user)
        except ProviderNotActive as pna:
            return inactive_provider(pna)
        except LibcloudInvalidCredsError:
            return invalid_creds(provider_uuid, identity_uuid)
        except LibcloudBadResponseError:
            return malformed_response(provider_uuid, identity_uuid)
        except (socket_error, ConnectionFailure):
            return connection_failure(provider_uuid, identity_uuid)
        except ObjectDoesNotExist:
            return invalid_provider_identity(provider_uuid, identity_uuid)
        except Exception as e:
            logger.exception("Unexpected exception for user:%s"
                             % request_user)
            return failure_response(status.HTTP_409_CONFLICT,
                                    e.message)
        serialized_data = ProviderMachineSerializer(filtered_machine_list,
                                                    request_user=request.user,
                                                    many=True).data
        response = Response(serialized_data)
        return response


def all_filtered_machines(user):
    return ProviderMachine.objects\
        .filter(application_version__application__created_by=user)\
        .exclude(
            Q(instance_source__identifier__startswith="eki-")
            | Q(instance_source__identifier__startswith="eri-"))\
        .order_by("-application_version__application__start_date")


class MachineHistory(AuthListAPIView):

    """Details about the machine history for an identity."""
    pagination_class = OptionalPagination

    serializer_class = ProviderMachineSerializer

    filter_backends = ()

    def get_queryset(self):
        return all_filtered_machines(self.request.user)


class MachineSearch(AuthListAPIView):

    """Provides server-side machine search for an identity."""
    filter_backends = ()

    pagination_class = OptionalPagination

    serializer_class = ProviderMachineSerializer

    def get_queryset(self):
        """
        """
        user = self.request.user
        query = self.request.query_params.get('query')
        identity_uuid = self.kwargs['identity_uuid']

        if not query:
            return ProviderMachine.objects.all()

        identity = Identity.objects.filter(uuid=identity_uuid).first()
        return search([CoreSearchProvider], identity, query)


class Machine(AuthAPIView):

    """
    Details about a specific machine, as seen by that identity.
    """

    def get(self, request, provider_uuid, identity_uuid, machine_id):
        """
        Details view for specific machine
        (Lookup using the given provider/identity)
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
        # TODO: Need to determine that identity_uuid is ALLOWED to
        # see machine_id. if not covered by calling as the users driver..
        esh_machine = esh_driver.get_machine(machine_id)
        core_machine = convert_esh_machine(esh_driver, esh_machine,
                                           provider_uuid, user)
        serialized_data = ProviderMachineSerializer(
            core_machine,
            request_user=request.user).data
        response = Response(serialized_data)
        return response

    def patch(self, request, provider_uuid, identity_uuid, machine_id):
        """
        Partially update the machine information
        (Lookup using the given provider/identity)
        """
        return self._update_machine(request, provider_uuid, identity_uuid,
                                    machine_id)

    def put(self, request, provider_uuid, identity_uuid, machine_id):
        """
        Update the machine information
        (Lookup using the given provider/identity)
        """
        return self._update_machine(request,
                                    provider_uuid,
                                    identity_uuid,
                                    machine_id)

    def _update_machine(self, request, provider_uuid, identity_uuid,
                        machine_id):
        # TODO: Determine who is allowed to edit machines besides
        # core_machine.owner
        user = request.user
        data = request.data
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
        esh_machine = esh_driver.get_machine(machine_id)
        core_machine = convert_esh_machine(esh_driver, esh_machine,
                                           provider_uuid, user)
        if not user.is_staff and user is not core_machine.application_version.application.created_by:
            logger.warn('%s is Non-staff/non-owner trying to update a machine'
                        % (user.username))
            return failure_response(
                status.HTTP_401_UNAUTHORIZED,
                "Only Staff and the machine Owner "
                "are allowed to change machine info.")

        partial_update = True if request.method == 'PATCH' else False
        serializer = ProviderMachineSerializer(core_machine,
                                               request_user=request.user,
                                               data=data,
                                               partial=partial_update)
        if serializer.is_valid():
            logger.info('metadata = %s' % data)
            update_machine_metadata(esh_driver, esh_machine, data)
            machine = serializer.save()
            if 'created_by_identity' in request.data:
                identity = machine.created_by_identity
                update_application_owner(
                    core_machine.application_version.application,
                    identity)
            logger.info(serializer.data)
            return Response(serializer.data)
        return failure_response(
            status.HTTP_400_BAD_REQUEST,
            serializer.errors)


class MachineIcon(AuthAPIView):

    """
    Represents:
        Calls to modify the single machine
    TODO: DELETE when we allow owners to 'end-date' their machine..
    """
    renderer_classes = (JPEGRenderer, PNGRenderer)

    def get(self, request, provider_uuid, identity_uuid, machine_id):
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
        # TODO: Need to determine that identity_uuid is ALLOWED to
        # see machine_id.
        # if not covered by calling as the users driver..
        esh_machine = esh_driver.get_machine(machine_id)
        core_machine = convert_esh_machine(esh_driver, esh_machine,
                                           provider_uuid, user)
        if not core_machine:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                "Could not retrieve machine with ID = %s" % machine_id)
        if not core_machine.application_version.application.icon:
            return None
        app_icon = core_machine.application_version.application.icon
        image_name, image_ext = os.path.splitext(app_icon.name)
        return Response(app_icon.file)


class MachineLicense(AuthAPIView):

    """
    Show list of all machine licenses applied.
    """

    def get(self, request, provider_uuid, identity_uuid, machine_id):
        """
        Lookup the machine information
        (Lookup using the given provider/identity)
        Update on server (If applicable)
        """
        core_machine = ProviderMachine.objects.filter(
            provider__uuid=provider_uuid,
            identifier=machine_id)
        if not core_machine:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                "Machine id %s does not exist" % machine_id)
        core_machine = core_machine.get()
        licenses = core_machine.licenses.all()
        serialized_data = LicenseSerializer(licenses, many=True).data
        return Response(serialized_data, status=status.HTTP_200_OK)

    def post(self, request, provider_uuid, identity_uuid, machine_id):
        """
        TODO: Determine who is allowed to edit machines besides
        core_machine.owner
        """
        user = request.user
        data = request.data

        logger.info('data = %s' % request.data)
        core_machine = ProviderMachine.objects.filter(
            provider__uuid=provider_uuid,
            identifier=machine_id)
        if not core_machine:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                "Machine id %s does not exist" % machine_id)

        core_machine = core_machine.get()
        if core_machine.instance_source.created_by == request.user:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                "You are NOT the owner of Machine id=%s " % machine_id)

        if 'licenses' not in data \
                or not isinstance(data['licenses'], list):
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                "Licenses missing from data. Expected a list of License IDs"
                " ex:[1,2,3,]")

        licenses = []
        # Out with the old
        core_machine.licenses.all().delete()
        for license_id in data['licenses']:
            license = License.objects.get(id=license_id)
            # In with the new
            core_machine.licenses.add(license)
        # Return the new set.
        licenses = core_machine.licenses.all()
        logger.info('licenses = %s' % licenses)
        serialized_data = LicenseSerializer(licenses, many=True).data
        return Response(serialized_data, status=status.HTTP_202_ACCEPTED)
