from rest_framework import status
from rest_framework.response import Response

from threepio import logger

from core.query import only_current_provider
from core.models.group import Group
from core.models.identity import Identity as CoreIdentity

from api.v1.serializers import CredentialDetailSerializer
from api import failure_response
from api.v1.views.base import AuthAPIView


def get_identity_list(user, provider=None):
    """
    Given the (request) user
    return all identities on all active providers
    """
    try:
        group = Group.objects.get(name=user.username)
        if provider:
            # Implicit: Active,non-end dated providers.
            identity_list = group.current_identities.filter(
                provider=provider)
        else:
            identity_list = group.current_identities.all()
        return identity_list
    except Group.DoesNotExist:
        logger.warn("Group %s DoesNotExist" % user.username)
        return None


def get_identity(user, identity_uuid):
    """
    Given the (request) user and an identity uuid,
    return None or an Active Identity
    """
    try:
        identity_list = get_identity_list(user)
        if not identity_list:
            raise CoreIdentity.DoesNotExist(
                "No identities found for user %s" % user.username)
        identity = identity_list.get(uuid=identity_uuid)
        return identity
    except CoreIdentity.DoesNotExist:
        logger.warn("Identity %s DoesNotExist" % identity_uuid)
        return None


class CredentialDetail(AuthAPIView):

    """
    The identity contains every credential necessary for atmosphere
    to connect 'The Provider' with a specific user.
    These credentials can vary from provider to provider.
    """

    def get(self, request, identity_uuid):
        """
        Authentication Required, all identities available to the user
        """
        identity = get_identity(request.user, identity_uuid)
        if not identity:
            return failure_response(
                status.HTTP_404_NOT_FOUND,
                "The requested Identity ID %s was not found "
                "on an active provider" % identity_uuid)
        serialized_data = CredentialDetailSerializer(identity).data
        return Response(serialized_data)


class CredentialList(AuthAPIView):

    """
    The identity contains every credential necessary for atmosphere
    to connect 'The Provider' with a specific user.
    These credentials can vary from provider to provider.
    """

    def get(self, request):
        """
        Authentication Required, all identities available to the user
        """
        identities = get_identity_list(request.user)
        serialized_data = CredentialDetailSerializer(identities,
                                                     many=True).data
        return Response(serialized_data)
