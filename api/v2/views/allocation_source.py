import uuid

from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from threepio import logger

from api.v2.exceptions import failure_response
from api.v2.serializers.details import AllocationSourceSerializer
from api.v2.views.base import AuthModelViewSet
from api.v2.views.mixins import MultipleFieldLookup
from core.models import AllocationSource, UserAllocationSource
from core.models.allocation_source import get_allocation_source_object
from core.models.event_table import EventTable


class AllocationSourceViewSet(MultipleFieldLookup, AuthModelViewSet):
    """
    API endpoint that allows scripts to be viewed or edited.
    """
    queryset = AllocationSource.objects.all()
    serializer_class = AllocationSourceSerializer
    search_fields = ('^name',)
    lookup_fields = ('id', 'uuid',)
    http_method_names = ['options', 'head', 'get', 'post', 'put', 'patch', 'delete']

    def get_queryset(self):
        """
        Get allocation sources for user
        """
        user = self.request.user
        sources = UserAllocationSource.objects.filter(user=user).values_list('allocation_source')
        return AllocationSource.objects.filter(id__in=sources)

    def create(self, request):
        """
        Create allocation source and fire respective events
        """

        if not hasattr(self, 'request'):
            self.request = request

        request_user = request.user
        request_data = request.data

        if not request_data.items():
            return failure_response(status.HTTP_400_BAD_REQUEST,
                                    "Reuquest Data is missing")

        try:
            self._validate_user(request_user)
        except Exception as exc:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                exc.message)

        try:
            self._validate_params(request_data)
        except Exception as exc:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                exc.message)

        try:
            allocation_source = self._create_allocation_source(request_data)
            # CHANGE SERIALIZER CLASS

            serialized_allocation_source = AllocationSourceSerializer(
                allocation_source, context={'request': self.request})
            return Response(
                serialized_allocation_source.data,
                status=status.HTTP_201_CREATED)

        except Exception as exc:
            logger.exception(
                "Encountered exception while creating Allocation Source")
            return failure_response(status.HTTP_409_CONFLICT,
                                    str(exc.message))

    def update(self, request, pk, *args, **fields):

        if not hasattr(self, 'request'):
            self.request = request

        request_user = request.user
        request_data = request.data
        request_data['source_id'] = pk
        request_data['allocation_source_name'] = AllocationSource.objects.filter(uuid=pk).last().name

        # check for data
        if not request_data.items():
            return failure_response(status.HTTP_400_BAD_REQUEST,
                                    "Request Data is missing")

        # validate user
        try:
            self._validate_user(request_user)
        except Exception as exc:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                exc.message)

        # validate patched fields and update allocation source model
        try:
            self._validate_params(request_data)

            # create payload
            payload = {}
            payload['allocation_source_name'] = request_data['allocation_source_name']

            # events to call
            events = []

            # if 'name' in request_data:
            #     payload_name = payload.copy()
            #     payload_name['name'] = request_data['name']
            #     events.append((
            #         'allocation_source_name_changed',
            #         payload_name))

            if 'renewal_strategy' in request_data:
                payload_renewal_strategy = payload.copy()
                payload_renewal_strategy['renewal_strategy'] = request_data['renewal_strategy']
                events.append((
                    'allocation_source_renewal_strategy_changed',
                    payload_renewal_strategy))

            if 'compute_allowed' in request_data:
                payload_compute_allowed = payload.copy()

                payload_compute_allowed['compute_allowed'] = request_data['compute_allowed']
                events.append((
                    'allocation_source_compute_allowed_changed',
                    payload_compute_allowed))

        except Exception as exc:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                exc.message)
        try:
            allocation_source = self._update_allocation_source(
                events, request_data)
            serialized_allocation_source = AllocationSourceSerializer(
                allocation_source, context={'request': self.request})
            return Response(
                serialized_allocation_source.data,
                status=status.HTTP_200_OK)

        except Exception as exc:
            logger.exception(
                "Encountered exception while updating Allocation Source")
            return failure_response(status.HTTP_409_CONFLICT,
                                    str(exc.message))

    def perform_destroy(self, allocation_source, request=None):

        if not hasattr(self, 'request'):
            self.request = request

        request_user = self.request.user
        request_data = {}
        request_data['allocation_source_name'] = allocation_source.name

        # validate user
        try:
            self._validate_user(request_user)
        except Exception as exc:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                exc.message)

        # validate patched fields and update allocation source model
        try:
            self._validate_params(request_data)
            # create payload
            payload = {}
            payload['allocation_source_name'] = str(request_data['allocation_source_name'])
            payload['delete_date'] = str(timezone.now().strftime("%Y-%m-%dT%H:%M:%S+00:00"))

            EventTable.create_event(
                'allocation_source_removed',
                payload,
                payload['allocation_source_name'])

        except Exception as exc:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                exc.message)

        try:
            allocation_source = allocation_source

            serialized_allocation_source = AllocationSourceSerializer(
                allocation_source, context={'request': self.request})
            return Response(
                serialized_allocation_source.data,
                status=status.HTTP_200_OK)

        except Exception as exc:
            logger.exception(
                "Encountered exception while removing Allocation Source")
            return failure_response(status.HTTP_409_CONFLICT,
                                    str(exc.message))

    # biz logic for actions

    def _create_allocation_source(self, request_data):

        payload = {}
        payload['uuid'] = str(uuid.uuid4())
        payload['allocation_source_name'] = request_data.get('name')
        payload['compute_allowed'] = request_data.get('compute_allowed')
        payload['renewal_strategy'] = request_data.get('renewal_strategy')

        creation_event = EventTable(
            name='allocation_source_created_or_renewed',
            entity_id=payload['allocation_source_name'],
            payload=payload)

        creation_event.save()

        return get_allocation_source_object(payload['uuid'])

    def _update_allocation_source(self, events, request_data):

        for event_name, payload in events:
            EventTable.create_event(
                event_name,
                payload,
                request_data['allocation_source_name']
            )

        return AllocationSource.objects.filter(name=request_data['allocation_source_name']).last()

    def _validate_params(self, data):

        if 'source_id' in data:
            self._for_validate_allocation_source(data['source_id'])

        if 'name' in data:
            self._for_validate_name(data['name'])

        if 'renewal_strategy' in data:
            self._for_validate_renewal_strategy(data['renewal_strategy'])

        if 'compute_allowed' in data:
            self._for_validate_compute_allowed(int(data['compute_allowed']), data.get('source_id'))

    # Common Validation

    def _validate_user(self, request_user):
        # user permission checking
        if not request_user.is_staff and not request_user.is_superuser:
            raise Exception('User not allowed to run commands')

    def _for_validate_compute_allowed(self, compute_allowed, source_id):
        # raise Exception('Error with Compute Allowed')

        # Compute Allowed always >= 1
        if compute_allowed < 0:
            raise Exception('Compute allowed cannot be less than 0')

        # Compute Allowed is less than compute used
        if source_id:
            allocation_source = get_allocation_source_object(source_id)
            if compute_allowed < allocation_source.compute_used:
                raise Exception('Compute allowed cannot be less than compute used')

        return True

    def _for_validate_renewal_strategy(self, renewal_strategy):
        # raise Exception('Error with Renewal Strategy')
        if renewal_strategy not in ['default', 'workshop', 'biweekly']:
            raise Exception(
                'Renewal Strategy %s is not valid' % (renewal_strategy))
        return True

    def _for_validate_allocation_source(self, source_id):
        get_allocation_source_object(source_id)
        return True

    def _for_validate_name(self, name):
        # raise Exception('Error with Allocation Source Name')
        return True
