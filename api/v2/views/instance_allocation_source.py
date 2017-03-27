
import django_filters

from django.conf import settings
from core.models import (
    AllocationSource, InstanceAllocationSourceSnapshot,EventTable, Instance, UserAllocationSource)
from core.models.allocation_source import get_allocation_source_object
from api.v2.serializers.details import AllocationSourceSerializer
from api.v2.serializers.details import InstanceAllocationSourceSerializer
from api.v2.views.base import AuthModelViewSet
from api.v2.views.mixins import MultipleFieldLookup
from rest_framework.decorators import detail_route
from rest_framework.response import Response
from api.v2.exceptions import failure_response
from rest_framework import status
from threepio import logger



class InstanceAllocationSourceViewSet(AuthModelViewSet):

    """
    API endpoint that allows scripts to be viewed or edited.
    """

    queryset = InstanceAllocationSourceSnapshot.objects.all()
    serializer_class = InstanceAllocationSourceSerializer
    search_fields = ("^title")
    lookup_fields = ("allocation_source__uuid", "id")
    http_method_names = ['options','head','get', 'post']

    def get_queryset(self):
        """
        Get user allocation source relationship
        """
        #user = self.get_object()
        return InstanceAllocationSourceSnapshot.objects.all()#filter(user__uuid=user)

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
            instance_allocation_source = self._create_instance_allocation_source(request_data, request_user)
            serialized_instance_allocation_source = InstanceAllocationSourceSerializer(
                instance_allocation_source, context={'request': self.request})
            return Response(
                serialized_instance_allocation_source.data,
                status=status.HTTP_201_CREATED)

        except Exception as exc:
            logger.exception(
                "Encountered exception while assigning Allocation source %s to Instance %s"
                %(request_data['source_id'], request_data['instance_id']))
            return failure_response(status.HTTP_409_CONFLICT,
                                    str(exc.message))


    #helper methods
    def _create_instance_allocation_source(self, request_data, request_user):

        payload = {}
        payload['instance_id'] = request_data.get('instance_id')
        payload['allocation_source_id'] = request_data.get('source_id')
        username=request_user.username

        creation_event = EventTable(
            name='instance_allocation_source_changed',
            entity_id=username,
            payload=payload)

        creation_event.save()
        allocation_source = get_allocation_source_object(request_data['source_id'])
        return InstanceAllocationSourceSnapshot.objects.filter(
            allocation_source=allocation_source,
            instance__provider_alias=payload['instance_id'] ).last()

    # validations

    def _validate_data(self,request_user, request_data):

        if not 'instance_id' in request_data:
            raise Exception('Missing Instance Provider Alias from request data ')

        if not 'source_id' in request_data:
            raise Exception('Missing Allocation Source Source ID from request data ')

        self._for_validate_userallocationsource(request_user,request_data)


    def _for_validate_userallocationsource(self,request_user,request_data):
        instance = Instance.objects.filter(provider_alias=request_data['instance_id']).last()
        allocation_source = get_allocation_source_object(request_data['source_id'])

        # The two validations below wont work in dev environment where the mock_user is lenards. Uncomment them in prod

        #if instance.created_by!=request_user:
        #    raise Exception('Instance %s does not belong to user %s' % (request_data['instance_id'],request_user.username))

        #if not UserAllocationSource.objects.filter(user=request_user,allocation_source=allocation_source):
        #    raise Exception(
        #        'Allocation Source %s is not assigned to user %s' % (request_data['source_id'], request_user.username))

        if InstanceAllocationSourceSnapshot.objects.filter(instance=instance,allocation_source=allocation_source):
            raise Exception('Instance %s is already assigned to Allocation Source %s'%(request_data['instance_id'],request_data['source_id']))
