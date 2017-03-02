import django_filters

from core.models import (
    AllocationSource, UserAllocationSource, AtmosphereUser, EventTable)
from api.v2.serializers.details import AllocationSourceSerializer
from api.v2.serializers.details import UserAllocationSourceSerializer
from api.v2.views.base import AuthModelViewSet
from api.v2.views.mixins import MultipleFieldLookup
from rest_framework.decorators import detail_route
from rest_framework.response import Response
from api.v2.exceptions import failure_response
from rest_framework import status
from threepio import logger



class UserAllocationSourceViewSet(AuthModelViewSet):

    """
    API endpoint that allows scripts to be viewed or edited.
    """

    queryset = UserAllocationSource.objects.all()
    serializer_class = UserAllocationSourceSerializer
    search_fields = ("^title")
    lookup_fields = ("allocation_source__source_id","id")
    http_method_names = ['options','head','get', 'post', 'delete']

    def get_queryset(self):
        """
        Get user allocation source relationship
        """
        #user = self.get_object()
        return UserAllocationSource.objects.all()#filter(user__uuid=user)

    # @detail_route(methods=['get'])
    # def user(self,request,pk=None):
    #     user = AtmosphereUser.objects.filter(uuid=pk).last()
    #     return Response([AllocationSourceSerializer(i.allocation_source,context={'request':request}).data for i in UserAllocationSource.objects.filter(user=user)])
    #

    def create(self,request):
        request_user = request.user
        request_data = request.data

        if not request_data.items():
            return failure_response(status.HTTP_400_BAD_REQUEST,
                                    "Reuquest Data is missing")

        try:
            self._validate_data(request_user,request_data)
        except Exception as exc:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                exc.message)

        try:
            user_allocation_source = self._create_user_allocation_source(request_data)
            serialized_user_allocation_source = UserAllocationSourceSerializer(
                user_allocation_source, context={'request': self.request})
            return Response(
                serialized_user_allocation_source.data,
                status=status.HTTP_201_CREATED)

        except Exception as exc:
            logger.exception(
                "Encountered exception while assigning Allocation source %s to User %s"
                %(request_data['source_id'], request_data['username']))
            return failure_response(status.HTTP_409_CONFLICT,
                                    str(exc.message))


    def delete(self,request):
        request_user = request.user
        request_data = request.data
        if not request_data.items():
            return failure_response(status.HTTP_400_BAD_REQUEST,
                                    "Reuquest Data is missing")

        try:
            self._validate_data(request_user,request_data,delete=True)
        except Exception as exc:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                exc.message)

        try:
            self._delete_user_allocation_source(request_data)
            return Response(
                status=status.HTTP_200_OK)

        except Exception as exc:
            logger.exception(
                "Encountered exception while removing User %s from Allocation source %s "
                % (request_data['username']),request_data['source_id'])
            return failure_response(status.HTTP_409_CONFLICT,
                                    str(exc.message))

    #helper methods
    def _create_user_allocation_source(self, request_data):

        payload = {}
        payload['username'] = request_data.get('username')
        payload['source_id'] = request_data.get('source_id')

        creation_event = EventTable(
            name='user_allocation_source_assigned',
            entity_id=payload['source_id'],
            payload=payload)

        creation_event.save()
        return UserAllocationSource.objects.filter(
            allocation_source__source_id=payload['source_id'],
            user__username=payload['username'] ).last()

    def _delete_user_allocation_source(self,request_data):

        payload = {}
        payload['source_id'] = request_data.get('source_id')
        payload['username'] = request_data.get('username')

        delete_event = EventTable(
            name='user_allocation_source_removed',
            entity_id=payload['source_id'],
            payload=payload)

        delete_event.save()


    # validations

    def _validate_data(self,request_user, request_data,delete=False):
        if not request_user.is_staff and not request_user.is_superuser:
            raise Exception('User not allowed to run commands')

        if not 'username' in request_data:
            raise Exception('Missing User from request data ')

        if not 'source_id' in request_data:
            raise Exception('Missing Allocation Source from request data ')

        self._for_validate_userallocationsource(request_data,delete)


    def _for_validate_userallocationsource(self,request_data,delete=False):
        user = AtmosphereUser.objects.filter(username=request_data['username'])
        allocation_source = AllocationSource.objects.filter(source_id=request_data['source_id'])

        if not user:
            raise Exception('Username %s does not exist'%(request_data['username']))

        if not allocation_source:
            raise Exception('Allocation Source %s does not exist'%(request_data['source_id']))

        user = user.last()
        allocation_source = allocation_source.last()

        if UserAllocationSource.objects.filter(user=user,allocation_source=allocation_source) and not delete:
            raise Exception('User %s is already assigned to Allocation Source %s'%(request_data['username'],request_data['source_id']))

        if not UserAllocationSource.objects.filter(user=user,allocation_source=allocation_source) and delete:
            raise Exception('User %s is not assigned to Allocation Source %s' % (
            request_data['username'], request_data['source_id']))
