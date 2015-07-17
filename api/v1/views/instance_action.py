
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import InstanceAction

from api import failure_response
from api.permissions import ApiAuthRequired, CloudAdminRequired,\
    InMaintenance
from api.v1.serializers import InstanceActionSerializer


class InstanceActionList(APIView):

    """
    Paginated list of all instance history for specific user.
    """

    permission_classes = (ApiAuthRequired,
                          InMaintenance,
                          CloudAdminRequired,)

    def get(self, request):
        """
        Authentication required, Retrieve a list of previously
        launched instances.
        """
        instance_actions = InstanceAction.objects.all()
        serialized_data = InstanceActionSerializer(
            instance_actions, many=True).data
        response = Response(serialized_data)
        return response


class InstanceActionDetail(APIView):

    """
    Instance history for specific instance.
    """

    permission_classes = (ApiAuthRequired,
                          InMaintenance,
                          CloudAdminRequired,)

    def get(self, request, action_id):
        """
        Authentication required, Retrieve a list of previously
        launched instances.
        """
        try:
            instance_action = InstanceAction.objects.get(id=action_id)
        except InstanceAction.DoesNotExist:
            return failure_response(status.HTTP_400_BAD_REQUEST,
                                    'Instance action ID=%s not found' %
                                    action_id)
        serialized_data = InstanceActionSerializer(instance_action).data
        response = Response(serialized_data)
        return response
