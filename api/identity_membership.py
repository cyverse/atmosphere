"""
Atmosphere service identity rest api.

"""

from rest_framework.reverse import reverse
from rest_framework.views import APIView
from rest_framework.response import Response

from threepio import logger

from authentication.decorators import api_auth_token_required

from core.models.group import Group
from core.models import IdentityMembership as CoreIdentityMembership

from api.serializers import IdentitySerializer


class IdentityMembershipList(APIView):
    """
    Represents:
        A List of people who are members of this identity
    """


    @api_auth_token_required
    def post(self, request, provider_id, identity_id, format=None):
        """
        Create a new identity member (ADMINS & OWNERS GROUP LEADERS ONLY)
        """
        user = request.user
        data = request.DATA
        try:
            identity = Identity.objects.get(id=identity_id)
        except Identity.DoesNotExist:
            raise Exception("Invalid identity id")

        if not identity.can_share(user):
            raise Exception("User %s cannot share identity %s. "
                            + "This incident will be reported")
        group_name = data['group']
        group = Group.objects.get(name=group_name)
        #Ensure provider_membership exists
        prov_member = identity.provider.share(group)
        id_member = identity.share(group)
        serializer = IdentitySerializer(id_member.identity)
        serialized_data = serializer.data
        return Response(serialized_data)


    @api_auth_token_required
    def get(self, request, provider_id, identity_id, format=None):
        """
        Return the credential information for this identity
        """
        #Sanity checks:
        # User is authenticated
        user = request.user
        # User is a member of a group ( TODO: loop through all instead)
        group = user.group_set.get(name=user.username)
        # Group has access to the active, running provider
        provider = group.providers.get(id=provider_id,
                                       active=True, end_date=None)
        # Group has access to the identity on that provider
        identity = group.identities.get(provider=provider, id=identity_id)
        # All other members of the identity are visible
        id_members = CoreIdentityMembership.objects.filter(
                identity__id=identity_id)
        return Response(IdentitySerializer(
            [id_member.identity for id_member in id_members],
            many=True).data)



class IdentityMembership(APIView):
    """
    Represents:
        Calls to modify the single Identity
    """
    @api_auth_token_required
    def delete(self, request, provider_id, identity_id, group_name, format=None):
        """
        Unshare the identity
        """
        try:
            identity = Identity.objects.get(id=identity_id)
        except Identity.DoesNotExist:
            raise Exception("Invalid identity id")

        if not identity.can_share(user):
            raise Exception("User %s cannot remove sharing from identity %s. "
                            + "This incident will be reported"
                            % (user, identity_id))
        group = Group.objects.get(name=group_name)
        id_member = identity.unshare(group)
        serializer = IdentitySerializer(id_member.identity)
        serialized_data = serializer.data
        return Response(serialized_data)

