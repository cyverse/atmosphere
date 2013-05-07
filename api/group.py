"""
Atmosphere service group rest api.

"""

from rest_framework.views import APIView
from rest_framework.response import Response

from threepio import logger

from authentication.decorators import api_auth_token_required

from core.models.group import Group as CoreGroup

from api.serializers import GroupSerializer

class GroupList(APIView):
    """
    Represents both the collection of groups
    AND
    Objects on the Group class
    TODO: LOCK THIS CLASS DOWN!!!
    """
    @api_auth_token_required
    def post(self, request):
        """
        Group Class:
        Create a new group in the database
        Returns success 200 OK - NO BODY on creation
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

    @api_auth_token_required
    def get(self, request):
        user = request.user
        all_groups = user.group_set.order_by('name')
        serialized_data = GroupSerializer(all_groups).data
        response = Response(serialized_data)
        return response


class Group(APIView):

    @api_auth_token_required
    def get(self, request, groupname):
        """
        Return the object belonging to the group
        as well as the 'default' provider/identity
        1. Test for authenticated groupname
        (Or if admin is the groupname for emulate functionality)
        2. <DEFAULT PROVIDER> Select first provider groupname can use
        3. <DEFAULT IDENTITY> Select first provider groupname can use
        4. Set in session THEN pass in response
        """
        logger.info(request.__dict__)
        user = request.user
        group = user.group_set.get(name=groupname)
        serialized_data = GroupSerializer(group).data
        response = Response(serialized_data)
        return response
