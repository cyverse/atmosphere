from rest_framework.response import Response
from api.v2.views.base import AuthViewSet
from rest_framework import status
from rest_framework.settings import api_settings
from api.v2.exceptions import failure_response
from threepio import logger
from core.models.allocation_source import AllocationSource
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
    ),

    2: AllocationSourceCommands(
    name='change_renewal_strategy',
    desc='Change Allocation Source Renewal Strategy'
    ),

    3: AllocationSourceCommands(
    name='change_allocation_source_name',
    desc='Change Allocation Source Name'
    ),

    4: AllocationSourceCommands(
        name='change_compute_allowed',
        desc='Change Allocation Source Compute Allowed'
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
                                    "Request Data is missing")

        if not request_data['action']:
            return failure_response(status.HTTP_400_BAD_REQUEST,
                                    "Command name is missing")

        try:
            self._validate_user(request_data,request_user)
        except Exception as exc:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                exc.message)

        action = str(request_data['action'])

        if action=='create_allocation_source':
            return self.create_allocation_source(request_data,request_user)
        elif action=='change_renewal_strategy':
            return self.change_renewal_strategy(request_data,request_user)
        elif action=='change_allocation_source_name':
            return self.change_allocation_source_name(request_data,request_user)
        elif action=='change_compute_allowed':
            return self.change_allocation_source_compute_allowed(request_data,request_user)
        else:
            return failure_response(status.HTTP_400_BAD_REQUEST,
                             "Incorrect command name")

    # Create Allocation Source

    def create_allocation_source(self,request_data,request_user):

        try:
            self._validate_for_allocation_source_creation(request_user,request_data)
        except Exception as exc:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                exc.message)

        try:
            allocation_source = self._create_allocation_source(request_data)
            serialized_allocation_source = AllocationSourceSerializer(
                allocation_source, context = {'request':self.request})
            return Response(serialized_allocation_source.data, status=status.HTTP_201_CREATED)

        except Exception as exc:
            logger.exception("Encountered exception while creating Allocation Source")
            return failure_response(status.HTTP_409_CONFLICT,
                                    str(exc.message))


    def _validate_for_allocation_source_creation(self, request_user, request_data):
        self._for_validate_compute_allowed(request_data['compute_allowed'])
        self._for_validate_renewal_strategy(request_data['renewal_strategy'])

    def _create_allocation_source(self,request_data):
        payload = {}
        payload['name'] = request_data.get('name')
        payload['compute_allowed'] = request_data.get('compute_allowed')
        payload['renewal_strategy'] = request_data.get('renewal_strategy')

        creation_event = EventTable(
             name='allocation_source_created',
             payload=payload)

        creation_event.save()
        return AllocationSource.objects.filter(source_id=creation_event.entity_id).last()

    # Change Renewal Strategy

    def change_renewal_strategy(self,request_data,request_user):
        try:
            self._validate_for_change_renewal_strategy(request_user,request_data)
        except Exception as exc:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                exc.message)
        try:
            allocation_source = self._change_renewal_strategy(request_data)
            serialized_allocation_source = AllocationSourceSerializer(
                allocation_source, context={'request': self.request})
            return Response(serialized_allocation_source.data, status=status.HTTP_201_CREATED)

        except Exception as exc:
            logger.exception("Encountered exception while changing renewal strategy")
            return failure_response(status.HTTP_409_CONFLICT,
                                    str(exc.message))

    def _validate_for_change_renewal_strategy(self,request_user,request_data):
        self._for_validate_allocation_source(request_data['source_id'])
        self._for_validate_renewal_strategy(request_data['renewal_strategy'])


    def _change_renewal_strategy(self, request_data):
        payload = {}
        payload['source_id'] = request_data['source_id']
        payload['renewal_strategy'] = request_data['renewal_strategy']

        EventTable.create_event('allocation_source_renewal_strategy_changed',
                                payload, payload['source_id'])

        return AllocationSource.objects.filter(
            source_id=request_data['source_id']).last()

    # Change Allocation Source Name

    def change_allocation_source_name(self, request_data, request_user):
        try:
            self._validate_for_change_allocation_source_name(request_user, request_data)
        except Exception as exc:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                exc.message)
        try:
            allocation_source = self._change_allocation_source_name(request_data)
            serialized_allocation_source = AllocationSourceSerializer(
                allocation_source, context={'request': self.request})
            return Response(serialized_allocation_source.data, status=status.HTTP_201_CREATED)

        except Exception as exc:
            logger.exception("Encountered exception while changing renewal strategy")
            return failure_response(status.HTTP_409_CONFLICT,
                                    str(exc.message))

    def _validate_for_change_allocation_source_name(self, request_user, request_data):
        self._for_validate_allocation_source(request_data['source_id'])
        self._for_validate_name(request_data['name'])

    def _change_allocation_source_name(self, request_data):
        payload = {}
        payload['source_id'] = request_data['source_id']
        payload['name'] = request_data['name']

        EventTable.create_event(
            'allocation_source_name_changed',
            payload,
            payload['source_id'])

        return AllocationSource.objects.filter(source_id=request_data['source_id']).last()

    # Change Allocation Source Compute Allowed

    def change_allocation_source_compute_allowed(self, request_data, request_user):
        try:
            self._validate_for_change_allocation_source_compute_allowed(request_user, request_data)
        except Exception as exc:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                exc.message)
        try:
            allocation_source = self._change_allocation_source_compute_allowed(request_data)
            serialized_allocation_source = AllocationSourceSerializer(
                allocation_source, context={'request': self.request})
            return Response(serialized_allocation_source.data, status=status.HTTP_201_CREATED)

        except Exception as exc:
            logger.exception("Encountered exception while changing renewal strategy")
            return failure_response(status.HTTP_409_CONFLICT,
                                    str(exc.message))

    def _validate_for_change_allocation_source_compute_allowed(self, request_user, request_data):
        self._for_validate_allocation_source(request_data['source_id'])
        self._for_validate_compute_allowed_delta(request_data['compute_allowed'])

    def _change_allocation_source_compute_allowed(self, request_data):
        payload = {}
        payload['source_id'] = request_data['source_id']
        payload['compute_allowed'] = request_data['compute_allowed']

        EventTable.create_event(
            'allocation_source_compute_allowed_changed',
            payload,
            payload['source_id'])

        return AllocationSource.objects.filter(source_id=request_data['source_id']).last()

    # Common Validations
    def _validate_user(self,request_data, request_user):
        # user permission checking
        if not request_user.is_staff and not request_user.is_superuser:
            raise Exception('User not allowed to run commands')

    def _for_validate_compute_allowed(self,compute_allowed):
        #raise Exception('Error with Compute Allowed')
        if int(compute_allowed)<0:
            raise Exception('Compute allowed cannot be less than 0')
        return True

    def _for_validate_compute_allowed_delta(self,compute_allowed):
        #raise Exception('Error with Compute Allowed')
        return True

    def _for_validate_renewal_strategy(self,renewal_strategy):
        #raise Exception('Error with Renewal Strategy')
        if renewal_strategy not in ['default','workshop','biweekly']:
            raise Exception('Renewal Strategy %s is not valid'%(renewal_strategy))
        return True

    def _for_validate_allocation_source(self,source_id):
        # raise Exception('Error with Source ID')
        return True

    def _for_validate_name(self,name):
        # raise Exception('Error with Allocation Source Name')
        return True
