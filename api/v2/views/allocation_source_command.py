from rest_framework.response import Response
from api.v2.views.base import AuthViewSet
from rest_framework import status
from rest_framework.settings import api_settings
from api.v2.exceptions import failure_response
from threepio import logger
from core.models.event_table import EventTable
from api.v2.serializers.details.allocation_source_command import AllocationSourceCommandSerializer
from api.v2.serializers.details.allocation_source import AllocationSourceSerializer

class AllocationSourceCommands:

    def __init__(self, name, desc):
        self.name = name
        self.desc = desc


#list of commands available

commands = {
    1: AllocationSourceCommands(
    name='create_allocation_source',
    desc='Create an Allocation Source'
    )

}

class AllocationSourceCommandViewSet(AuthViewSet):
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES
    serializer_class = AllocationSourceCommandSerializer

    def list(self, request):
        serializer = AllocationSourceCommandSerializer(
            instance = commands.values(), many=True)
        return Response(serializer.data)

    def create(self, request):
        request_user = request.user
        request_data = request.data

        if not request_data.items():
            return failure_response(status.HTTP_400_BAD_REQUEST,
                                    "The allocation source creation API should be accessed via the query parameters:"
                                    " ['source_id', 'name', 'compute_allowed', 'renewal_strategy']")

        try:
            self._validate_input(request_data,request_user)
        except Exception as exc:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                exc.message)

        try:
            allocation_source = self._create_allocation_source(request_data)
            serialized_allocation_source = AllocationSourceSerializer(
                allocation_source, context = {'request':self.request})
            return Response(serialized_allocation_source, status=status.HTTP_201_CREATED)

        except Exception as exc:
            logger.exception("Encountered exception while creating Allocation Source")
            return failure_response(status.HTTP_409_CONFLICT,
                                    str(exc.message))

    @staticmethod
    def _validate_input(self,request_data, request_user):
        # user permission checking
        if not request_user.is_staff and not request_user.is_superuser:
            raise Exception('User not allowed to create Allocation Source')

        # check compute allowed and renewal strategy
        self._for_validate_compute_allowed(request_data['compute_allowed'])
        self._for_validate_renewal_strategy(request_data['renewal_strategy'])

    @staticmethod
    def _for_validate_compute_allowed(self,compute_allowed):
        #raise Exception('Error with Compute Allowed')
        return True

    @staticmethod
    def _for_validate_renewal_strategy(self,renewal_strategy):
        #raise Exception('Error with Renewal Strategy')
        return True

    @staticmethod
    def _create_allocation_source(self,request_data):
        payload = {}
        payload['source_id'] = request_data.get('source_id')
        payload['name'] = request_data.get('name')
        payload['compute_allowed'] = request_data.get('compute_allowed')
        payload['renewal_strategy'] = request_data.get('renewal_strategy')

        return EventTable.create_event(
            'allocation_source_created',
             payload,
             payload['source_id'])


