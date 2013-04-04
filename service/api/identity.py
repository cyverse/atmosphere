"""
Atmosphere service identity rest api.

"""

from rest_framework.reverse import reverse
from rest_framework.views import APIView
from rest_framework.response import Response

from atmosphere.logger import logger

from authentication.decorators import api_auth_token_required

from core.models.group import Group

from service.api.serializers import IdentitySerializer


class IdentityList(APIView):
    """
    Represents:
        A List of Identity
        Calls to the Identity Class
    """
    @api_auth_token_required
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
        serialized_data = IdentitySerializer(identities).data
        return Response(serialized_data)


class Identity(APIView):
    """
    Represents:
        Calls to modify the single Identity
    """
    @api_auth_token_required
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
