from rest_framework.reverse import reverse
from rest_framework.views import APIView
from rest_framework.response import Response

from threepio import logger


from core.models.group import Group
from core.models.identity import Identity as CoreIdentity

from api import failure_response
from api.serializers import IdentitySerializer, IdentityDetailSerializer
from api.permissions import InMaintenance, ApiAuthRequired

class IdentityDetail(APIView):
    """The identity contains every credential necessary for atmosphere to connect 'The Provider' with a specific user.
    These credentials can vary from provider to provider.
    """

    permission_classes = (ApiAuthRequired,)

    def get(self, request, identity_uuid):
        """
        Authentication Required, all identities available to the user
        """
        #NOTE: This is actually all Identities belonging to the group matching the username
        #TODO: This should be user, user.groups.all, etc. to account for future 'shared' identitys
        username = request.user.username
        group = Group.objects.get(name=username)
        providers = group.providers.filter(active=True, end_date=None)
        identity = None
        for p in providers:
            try:
                identity = group.identities.get(provider=p, uuid=identity_uuid)
            except CoreIdentity.DoesNotExist:
                pass
        if not identity:
            return failure_response(
                status.HTTP_404_NOT_FOUND,
                "The requested Identity ID %s was not found on an active provider"
                % identity_uuid)
        serialized_data = IdentityDetailSerializer(identity).data
        return Response(serialized_data)


class IdentityDetailList(APIView):
    """The identity contains every credential necessary for atmosphere to connect 'The Provider' with a specific user.
    These credentials can vary from provider to provider.
    """

    permission_classes = (ApiAuthRequired,)

    def get(self, request):
        """
        Authentication Required, all identities available to the user
        """
        #NOTE: This is actually all Identities belonging to the group matching the username
        #TODO: This should be user, user.groups.all, etc. to account for future 'shared' identitys
        username = request.user.username
        group = Group.objects.get(name=username)
        providers = group.providers.filter(active=True, end_date=None)
        identities = []
        for p in providers:
            [identities.append(i) for i in group.identities.filter(provider=p).order_by('id')]
        serialized_data = IdentityDetailSerializer(identities, many=True).data
        return Response(serialized_data)


class IdentityList(APIView):
    """The identity contains every credential necessary for atmosphere to connect 'The Provider' with a specific user.
    These credentials can vary from provider to provider.
    """

    permission_classes = (ApiAuthRequired,)
    
    def get(self, request, provider_uuid, format=None):
        """
        List of identities for the user on the selected provider.
        """
        #NOTE: Identity's belonging to the group matching the username
        #TODO: This should be user, user.groups.all, etc. to account for
        #future 'shared' identitys
        username = request.user.username
        group = Group.objects.get(name=username)
        provider = group.providers.get(uuid=provider_uuid,
                                       active=True, end_date=None)

        identities = group.identities.filter(provider=provider).order_by('id')
        serialized_data = IdentitySerializer(identities, many=True).data
        return Response(serialized_data)


class Identity(APIView):
    """The identity contains every credential necessary for atmosphere to connect 'The Provider' with a specific user.
    These credentials can vary from provider to provider.
    """

    permission_classes = (ApiAuthRequired,)
    
    def get(self, request, provider_uuid, identity_uuid, format=None):
        """
        Authentication Required, Get details for a specific identity.
        """
        username = request.user.username
        group = Group.objects.get(name=username)
        provider = group.providers.get(uuid=provider_uuid,
                                       active=True, end_date=None)

        identity = group.identities.get(provider=provider, uuid=identity_uuid)
        serialized_data = IdentitySerializer(identity).data
        logger.debug(type(serialized_data))
        return Response(serialized_data)
