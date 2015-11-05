from django.core.exceptions import ObjectDoesNotExist

from rest_framework import status
from rest_framework.response import Response

from threepio import logger

from core.models.group import Group
from core.models import IdentityMembership as CoreIdentityMembership
from core.query import only_current_provider

from api import failure_response
from api.v1.serializers import IdentitySerializer
from api.v1.views.base import AuthAPIView


class IdentityMembershipList(AuthAPIView):

    """
    A List of people who are members of this identity.
    """

    def post(self, request, provider_uuid, identity_uuid, format=None):
        """
        Create a new identity member (ADMINS & OWNERS GROUP LEADERS ONLY)
        """
        user = request.user
        data = request.data
        try:
            identity = Identity.objects.get(uuid=identity_uuid)
            group_name = data['group']
            group = Group.objects.get(name=group_name)
        except ObjectDoesNotExist as odne:
            return failure_response(
                status.HTTP_404_NOT_FOUND,
                '%s does not exist.' % odne.message.split()[0])
        if not identity.can_share(user):
            return failure_response(
                status.HTTP_401_UNAUTHORIZED,
                "User %s cannot remove sharing from identity %s. "
                "This incident will be reported"
                % (user, identity_uuid))
        id_member = identity.share(group)
        serializer = IdentitySerializer(id_member.identity)
        serialized_data = serializer.data
        return Response(serialized_data)

    def get(self, request, provider_uuid, identity_uuid, format=None):
        """
        Return the identity membership matching this provider+identity
        """
        # Sanity checks:
        # User is authenticated
        user = request.user
        try:
            # User is a member of a group ( TODO: loop through all instead)
            group = user.group_set.get(name=user.username)
            # Group has access to the identity on an active,
            # currently-running provider
            identity = group.current_identities.get(
                                            uuid=identity_uuid)
            # All other members of the identity are visible
            id_members = CoreIdentityMembership.objects.filter(
                identity__uuid=identity_uuid)
        except ObjectDoesNotExist as odne:
            return failure_response(
                status.HTTP_404_NOT_FOUND,
                '%s does not exist.' % odne.message.split()[0])
        id_list = [id_member.identity for id_member in id_members[:1]]
        serializer = IdentitySerializer(id_list, many=True)
        serialized_data = serializer.data
        return Response(serialized_data)


class IdentityMembership(AuthAPIView):

    """
    IdentityMembership details for a specific group/identity combination.
    """

    def delete(self, request, provider_uuid,
               identity_uuid, group_name, format=None):
        """
        Unshare the identity.
        """
        try:
            identity = Identity.objects.get(uuid=identity_uuid)
        except Identity.DoesNotExist:
            return failure_response(
                status.HTTP_404_NOT_FOUND,
                "Identity does not exist.")
        if not identity.can_share(user):
            logger.error(
                "User %s cannot remove sharing from identity %s. "
                "This incident will be reported"
                % (user, identity_uuid))
            return failure_response(
                status.HTTP_401_UNAUTHORIZED,
                "User %s cannot remove sharing from identity %s. "
                "This incident will be reported"
                % (user, identity_uuid))
        group = Group.objects.get(name=group_name)
        id_member = identity.unshare(group)
        serializer = IdentitySerializer(id_member.identity)
        serialized_data = serializer.data
        return Response(serialized_data)
