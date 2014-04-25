from rest_framework.reverse import reverse
from rest_framework.views import APIView
from rest_framework.response import Response

from threepio import logger


from core.models.group import Group

from api.serializers import IdentitySerializer, IdentityDetailSerializer
from api.permissions import InMaintenance, ApiAuthRequired

class IdentityDetailList(APIView):
    """A Detailed List of Identities for request_user"""

    permission_classes = (ApiAuthRequired,)

    def get(self, request):
        """
        List of identity that match USER and the provider_id
        * Identity's belonging to the group matching the username
        TODO: This should be user, user.groups.all, etc. to account for
        future 'shared' identitys
        """
        username = request.user.username
        group = Group.objects.get(name=username)
        providers = group.providers.filter(active=True, end_date=None)
        identities = []
        for p in providers:
            [identities.append(i) for i in group.identities.filter(provider=p).order_by('id')]
        serialized_data = IdentityDetailSerializer(identities, many=True).data
        return Response(serialized_data)


class IdentityList(APIView):
    """A List of Identities for request_user"""

    permission_classes = (ApiAuthRequired,)
    
    def get(self, request, provider_id, format=None):
        """
        List of identity that match USER and the provider_id
        * Identity's belonging to the group matching the username
        TODO: This should be user, user.groups.all, etc. to account for
        future 'shared' identitys
        """
        username = request.user.username
        group = Group.objects.get(name=username)
        provider = group.providers.get(id=provider_id,
                                       active=True, end_date=None)

        identities = group.identities.filter(provider=provider).order_by('id')
        serialized_data = IdentitySerializer(identities, many=True).data
        return Response(serialized_data)


class Identity(APIView):
    """Details about specific identity."""

    permission_classes = (ApiAuthRequired,)
    
    def get(self, request, provider_id, identity_id, format=None):
        """
        Return the credential information for this identity
        """
        username = request.user.username
        group = Group.objects.get(name=username)
        provider = group.providers.get(id=provider_id,
                                       active=True, end_date=None)

        identity = group.identities.get(provider=provider, id=identity_id)
        serialized_data = IdentitySerializer(identity).data
        logger.debug(type(serialized_data))
        return Response(serialized_data)
