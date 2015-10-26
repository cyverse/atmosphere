"""
Atmosphere service group rest api.

"""
from rest_framework.response import Response

from threepio import logger

from core.models.group import Group as CoreGroup

from api.v1.serializers import GroupSerializer
from api.v1.views.base import AuthAPIView


class GroupList(AuthAPIView):

    """
    Every User is assigned to a Group of their own name initially. This
    'usergroup' is then in charge of all the identities, providers, instances,
    and applications which can be shared among other, larger groups, but can
    still be tracked back to the original user who made the API request.
    """

    def post(self, request):
        """
        Authentication Required, Create a new group.

        Params:name -- The name of the group
               user -- One or more users belonging to the group
        """
        params = request.data
        groupname = params['name']
        # STEP1 Create the account on the provider
        group = CoreGroup.objects.create(name=groupname)
        # STEP2 ???? PROFIT ????
        for user in params['user[]']:
            group.user_set.add(user)
        # STEP3 Return the new groups serialized profile
        serialized_data = GroupSerializer(group).data
        response = Response(serialized_data)
        return response

    def get(self, request):
        """
        Authentication Required, A list of all the user's groups.
        """
        user = request.user
        all_groups = user.group_set.order_by('name')
        serialized_data = GroupSerializer(all_groups).data
        response = Response(serialized_data)
        return response


class Group(AuthAPIView):

    """
    Every User is assigned to a Group of their own name initially. This
    'usergroup' is then in charge of all the identities, providers, instances,
    and applications which can be shared among other, larger groups, but can
    still be tracked back to the original user who made the API request.
    """

    def get(self, request, groupname):
        """
        Authentication Required, Retrieve details about a specific group.
        """
        logger.info(request.__dict__)
        user = request.user
        group = user.group_set.get(name=groupname)
        serialized_data = GroupSerializer(group).data
        response = Response(serialized_data)
        return response
