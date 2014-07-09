"""
Atmosphere service machine rest api.

"""
import os
from django.core.paginator import Paginator,\
    PageNotAnInteger, EmptyPage
from django.db.models import Q

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from threepio import logger

from core.models import AtmosphereUser as User
from core.models.application import ApplicationScore
from core.models.identity import Identity
from core.models.machine import compare_core_machines, filter_core_machine,\
    update_application_owner, convert_esh_machine, ProviderMachine
from core.metadata import update_machine_metadata

from service.search import search, CoreSearchProvider

from api import prepare_driver, failure_response, invalid_creds
from api.renderers import JPEGRenderer, PNGRenderer
from api.permissions import InMaintenance, ApiAuthRequired
from api.serializers import ProviderMachineSerializer,\
    PaginatedProviderMachineSerializer, ApplicationScoreSerializer


def provider_filtered_machines(request, provider_id,
                               identity_id, request_user=None):
    """
    Return all filtered machines. Uses the most common,
    default filtering method.
    """
    esh_driver = prepare_driver(request, provider_id, identity_id)
    if not esh_driver:
        return invalid_creds(provider_id, identity_id)
    return list_filtered_machines(esh_driver, provider_id, request_user)


def list_filtered_machines(esh_driver, provider_id, request_user=None):
    esh_machine_list = esh_driver.list_machines()
    #logger.info("Total machines from esh:%s" % len(esh_machine_list))
    esh_machine_list = esh_driver.filter_machines(
        esh_machine_list,
        black_list=['eki-', 'eri-'])
    #logger.info("Filtered machines from esh:%s" % len(esh_machine_list))
    core_machine_list = [convert_esh_machine(esh_driver, mach,
                                             provider_id, request_user)
                         for mach in esh_machine_list]
    #logger.info("Core machines :%s" % len(core_machine_list))
    filtered_machine_list = [core_mach for core_mach in core_machine_list
                             if filter_core_machine(core_mach)]
    #logger.info("Filtered Core machines :%s" % len(filtered_machine_list))
    sorted_machine_list = sorted(filtered_machine_list,
                                 cmp=compare_core_machines)
    return sorted_machine_list


def all_filtered_machines():
    return ProviderMachine.objects.exclude(
        Q(identifier__startswith="eki-")
        | Q(identifier__startswith="eri")).order_by("-application__start_date")


class MachineList(APIView):
    """List of machines."""

    permission_classes = (InMaintenance, ApiAuthRequired)

    def get(self, request, provider_id, identity_id):
        """
        Using provider and identity, getlist of machines
        TODO: Cache this request
        """
        try:
            request_user = request.user
            filtered_machine_list = provider_filtered_machines(request,
                                                               provider_id,
                                                               identity_id,
                                                               request_user)
        except InvalidCredsError:
            return invalid_creds(provider_id, identity_id)
        except:
            logger.exception("Unexpected exception for user:%s"
                             % request_user)
            return invalid_creds(provider_id, identity_id)
        serialized_data = ProviderMachineSerializer(filtered_machine_list,
                                                    request_user=request.user,
                                                    many=True).data
        response = Response(serialized_data)
        return response


class MachineHistory(APIView):
    """Details about the machine history for an identity."""

    permission_classes = (InMaintenance, ApiAuthRequired)

    def get(self, request, provider_id, identity_id):
        data = request.DATA
        user = User.objects.filter(username=request.user)

        if user and len(user) > 0:
            user = user[0]
        else:
            return failure_response(
                status.HTTP_401_UNAUTHORIZED,
                "User not found.")
        esh_driver = prepare_driver(request, provider_id, identity_id)
        if not esh_driver:
            return invalid_creds(provider_id, identity_id)
        # Historic Machines
        all_machines_list = all_filtered_machines()
        if all_machines_list:
            history_machine_list =\
                [m for m in all_machines_list if
                 m.application.created_by.username == user.username]
        else:
            history_machine_list = []

        page = request.QUERY_PARAMS.get('page')
        if page or len(history_machine_list) == 0:
            paginator = Paginator(history_machine_list, 5,
                                  allow_empty_first_page=True)
        else:
            paginator = Paginator(history_machine_list,
                                  len(histor_machine_list),
                                  allow_empty_first_page=True)
        try:
            history_machine_page = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            history_machine_page = paginator.page(1)
        except EmptyPage:
            # Page is out of range.
            # deliver last page of results.
            history_machine_page = paginator.page(paginator.num_pages)
        serialized_data = PaginatedProviderMachineSerializer(
            history_machine_page).data
        response = Response(serialized_data)
        response['Cache-Control'] = 'no-cache'
        return response


def get_first(coll):
    """
    Return the first element of a collection, otherwise return False.
    """
    if coll and len(coll) > 0:
        return coll[0]
    else:
        return False


class MachineSearch(APIView):
    """Provides server-side machine search for an identity."""

    permission_classes = (InMaintenance, ApiAuthRequired)

    def get(self, request, provider_id, identity_id):
        """
        """
        data = request.DATA
        user = get_first(User.objects.filter(username=request.user))
        if not user:
            return failure_response(
                status.HTTP_401_UNAUTHORIZED,
                "User not found.")
        query = request.QUERY_PARAMS.get('query')
        if not query:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                "Query not provided.")
        identity = get_first(Identity.objects.filter(id=identity_id))
        if not identity:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                'Identity not provided,')
        search_result = search([CoreSearchProvider], identity, query)
        page = request.QUERY_PARAMS.get('page')
        if page or len(search_result) == 0:
            paginator = Paginator(search_result, 20,
                                  allow_empty_first_page=True)
        else:
            paginator = Paginator(search_result, len(search_result),
                                  allow_empty_first_page=True)
        try:
            search_page = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            search_page = paginator.page(1)
        except EmptyPage:
            # Page is out of range.
            # deliver last page of results.
            search_page = paginator.page(paginator.num_pages)
        serialized_data = PaginatedProviderMachineSerializer(
            search_page).data
        response = Response(serialized_data)
        response['Cache-Control'] = 'no-cache'
        return response


class Machine(APIView):
    """Details about a specific machine, as seen by that identity."""

    permission_classes = (ApiAuthRequired,)

    def get(self, request, provider_id, identity_id, machine_id):
        """
        Details view for specific machine
        (Lookup using the given provider/identity)
        """
        user = request.user
        esh_driver = prepare_driver(request, provider_id, identity_id)
        if not esh_driver:
            return invalid_creds(provider_id, identity_id)
        #TODO: Need to determine that identity_id is ALLOWED to see machine_id.
        #     if not covered by calling as the users driver..
        esh_machine = esh_driver.get_machine(machine_id)
        core_machine = convert_esh_machine(esh_driver, esh_machine,
                                           provider_id, user)
        serialized_data = ProviderMachineSerializer(
            core_machine,
            request_user=request.user).data
        response = Response(serialized_data)
        return response

    def patch(self, request, provider_id, identity_id, machine_id):
        """
        Partially update the machine information
        (Lookup using the given provider/identity)
        """
        return self._update_machine(request, provider_id, identity_id, machine_id)

    def put(self, request, provider_id, identity_id, machine_id):
        """
        Update the machine information
        (Lookup using the given provider/identity)
        """
        return self._update_machine(request, provider_id, identity_id, machine_id)

    def _update_machine(self, request, provider_id, identity_id, machine_id):
        #TODO: Determine who is allowed to edit machines besides
        #core_machine.owner
        user = request.user
        data = request.DATA
        esh_driver = prepare_driver(request, provider_id, identity_id)
        if not esh_driver:
            return invalid_creds(provider_id, identity_id)
        esh_machine = esh_driver.get_machine(machine_id)
        core_machine = convert_esh_machine(esh_driver, esh_machine,
                                           provider_id, user)
        if not user.is_staff\
           and user is not core_machine.application.created_by:
            logger.warn('%s is Non-staff/non-owner trying to update a machine'
                        % (user.username))
            return failure_response(
                status.HTTP_401_UNAUTHORIZED,
                "Only Staff and the machine Owner "
                + "are allowed to change machine info.")

        partial_update = True if request.method == 'PATCH' else False
        serializer = ProviderMachineSerializer(core_machine,
                                               request_user=request.user,
                                               data=data,
                                               partial=partial_update)
        if serializer.is_valid():
            logger.info('metadata = %s' % data)
            update_machine_metadata(esh_driver, esh_machine, data)
            serializer.save()
            if 'created_by_identity' in request.DATA:
                identity = serializer.object.created_by_identity
                update_application_owner(core_machine.application, identity)
            logger.info(serializer.data)
            return Response(serializer.data)
        return failure_response(
            status.HTTP_400_BAD_REQUEST,
            serializer.errors)


class MachineIcon(APIView):
    """
    Represents:
        Calls to modify the single machine
    TODO: DELETE when we allow owners to 'end-date' their machine..
    """
    renderer_classes = (JPEGRenderer, PNGRenderer)
    permission_classes = (ApiAuthRequired)

    def get(self, request, provider_id, identity_id, machine_id):
        user = request.user
        esh_driver = prepare_driver(request, provider_id, identity_id)
        if not esh_driver:
            return invalid_creds(provider_id, identity_id)
        #TODO: Need to determine that identity_id is ALLOWED to see machine_id.
        #     if not covered by calling as the users driver..
        esh_machine = esh_driver.get_machine(machine_id)
        core_machine = convert_esh_machine(esh_driver, esh_machine,
                                           provider_id, user)
        if not core_machine:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                "Could not retrieve machine with ID = %s" % machine_id)
        if not core_machine.application.icon:
            return None
        app_icon = core_machine.application.icon
        image_name, image_ext = os.path.splitext(app_icon.name)
        return Response(app_icon.file)


class MachineVote(APIView):
    """Rate the selected image by voting."""

    permission_classes = (ApiAuthRequired,)

    def get(self, request, provider_id, identity_id, machine_id):
        """
        Lookup the machine information
        (Lookup using the given provider/identity)
        Update on server (If applicable)
        """
        core_machine = ProviderMachine.objects.filter(provider__id=provider_id,
                                                      identifier=machine_id)
        if not core_machine:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                "Machine id %s does not exist" % machine_id)

        app = core_machine[0].application
        vote = ApplicationScore.last_vote(app, request.user)
        serialized_data = ApplicationScoreSerializer(vote).data
        return Response(serialized_data, status=status.HTTP_201_CREATED)

    def post(self, request, provider_id, identity_id, machine_id):
        """
        TODO: Determine who is allowed to edit machines besides
        core_machine.owner
        """
        user = request.user
        data = request.DATA
        if 'vote' not in data:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                "Vote missing from data")
        vote = data['vote']

        core_machine = ProviderMachine.objects.filter(provider__id=provider_id,
                                                      identifier=machine_id)
        if not core_machine:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                "Machine id %s does not exist" % machine_id)

        app = core_machine[0].application

        if 'up' in vote:
            vote = ApplicationScore.upvote(app, user)
        elif 'down' in vote:
            vote = ApplicationScore.downvote(app, user)
        else:
            vote = ApplicationScore.novote(app, user)

        serialized_data = ApplicationScoreSerializer(vote).data
        return Response(serialized_data, status=status.HTTP_201_CREATED)
