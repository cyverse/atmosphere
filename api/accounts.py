"""
Atmosphere service accounts rest api.
"""
import copy

from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from threepio import logger

from atmosphere import settings

from authentication.decorators import api_auth_token_required

from core.models import AtmosphereUser as User
from core.models.provider import Provider as CoreProvider
from core.models.identity import Identity as CoreIdentity

from service.accounts.openstack import AccountDriver as OSAccountDriver
from service.accounts.eucalyptus import AccountDriver as EucaAccountDriver
from service.accounts.aws import AccountDriver as AWSAccountDriver

from api.serializers import AccountSerializer, IdentitySerializer


def get_account_driver(provider_id):
    try:
        provider = Provider.objects.get(id=provider_id)
    except CoreProvider.DoesNotExist:
        return Response(
            'No provider matching id %s' % provider_id,
            status=status.HTTP_404_NOT_FOUND)
    #TODO: We need better logic here. maybe use provider name?
    provider_name = provider.location.lower()
    #TODO: How we select args will change..
    if 'openstack' in provider_name:
        driver = OSAccountDriver(provider)
    elif 'eucalyptus' in provider_name:
        driver = EucaAccountDriver(provider)
    #elif 'aws' in provider_name:
    #    driver = AWSAccountDriver(provider)
    else:
        raise Exception("Could not find a driver for provider %s" %
                        provider_name)
    return driver


class AccountManagement(APIView):
    """
    This API is used to provide account management.
    provider_id -- The id of the provider whose account you want to manage.
    """

    @api_auth_token_required
    def get(self, request, provider_id):
        """
        Return a list of ALL users found on provider_id
        """
        pass
        #driver = get_account_driver(provider_id)
        ##TODO: Maybe get_or_create identity on list_users?
        #users = driver.list_users()
        ##Maybe identities?
        #serialized_data = AccountSerializer(users).data
        #response = Response(serialized_data)
        #return response


class Account(APIView):
    """
    This API is used to create/update/list/delete a specific user identity
    provider_id -- The id of the provider whose account you want to manage.
    """

    @api_auth_token_required
    def get(self, request, provider_id, username):
        """
        Detailed view of all identities for provider,user combination.
        username -- The username to match identities
        """
        identities = CoreIdentity.objects.filter(provider__id=provider_id,
                                                 created_by__username=username)
        serialized_data = IdentitySerializer(identities, many=True).data
        return Response(serialized_data)

    @api_auth_token_required
    def post(self, request, provider_id, username):
        """
        Create a new account on provider for this username
        POST data should have all credentials required for this provider
        username -- The username who created the identity
        """
        user = request.user
        data = request.DATA

        driver = get_account_driver(provider_id)
        missing_args = driver.clean_credentials(data)
        if missing_args:
            raise Exception("Cannot create account. Missing credentials: %s"
                            % missing_args)
        identity = driver.create_account(**data)
        serializer = IdentityDetailSerializer(identity)
        if serializer.is_valid():
            #NEVER FAILS
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
