"""
Atmosphere service group rest api.

"""

from rest_framework.views import APIView
from rest_framework.response import Response

from threepio import logger


from core.models.group import Group as CoreGroup

from api.permissions import InMaintenance, ApiAuthOptional, ApiAuthRequired
from api.serializers import GroupSerializer

class GroupList(APIView):
    """List groups"""
    permission_classes = (ApiAuthRequired,)

    def post(self, request):
        """
        """
        params = request.DATA
        groupname = params['name']
        #STEP1 Create the account on the provider
        group = CoreGroup.objects.create(name=groupname)
        for user in params['user[]']:
                group.user_set.add(user)
        #STEP3 Return the new groups serialized profile
        serialized_data = GroupSerializer(group).data
        response = Response(serialized_data)
        return response

    
    def get(self, request):
        """
        """
        user = request.user
        all_groups = user.group_set.order_by('name')
        serialized_data = GroupSerializer(all_groups).data
        response = Response(serialized_data)
        return response


class Group(APIView):
    """Detailed view about group

    groupname -- Name of group
    """

    permission_classes = (ApiAuthRequired,)

    def get(self, request, groupname):
        """
        """
        logger.info(request.__dict__)
        user = request.user
        group = user.group_set.get(name=groupname)
        serialized_data = GroupSerializer(group).data
        response = Response(serialized_data)
        return response
