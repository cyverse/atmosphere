"""
Atmosphere service user rest api.

"""
from django.contrib.auth.models import User as AuthUser

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from atmosphere import settings
from atmosphere.logger import logger

from auth.decorators import api_auth_token_required

from core.models.group import Group
from core.models.profile import getDefaultProvider, getDefaultIdentity

from service.accounts.eucalyptus import AccountDriver
from service.api.serializers import ProfileSerializer


class UserManagement(APIView):
    """
    Represents both the collection of users
    AND
    Objects on the User class
    TODO: LOCK THIS CLASS DOWN!!!
    """
    @api_auth_token_required
    def post(self, request):
        """
        User Class:
        Create a new user in the database
        Returns success 200 OK - NO BODY on creation
        """
        params = request.DATA
        user = request.user
        if user.username is not 'admin' or not user.is_superuser:
            return Response('Only admin and superusers can create accounts', status=status.HTTP_401_UNAUTHORIZED)

        username = params['username']
        #STEP1 Create the account on the provider
        driver = AccountDriver(settings.EUCA_ADMIN_KEY, settings.EUCA_ADMIN_SECRET, settings.EUCA_EC2_URL)
        user= driver.add_user(username)
        #STEP2 Retrieve the identity from the provider
        if user:
            user_keys = driver.get_key(username)
            key = driver.create_key(user_keys)
        #STEP3 Return the new users serialized profile
        serialized_data = ProfileSerializer(user.get_profile()).data
        response = Response(serialized_data)
        return response

    @api_auth_token_required
    def get(self, request):
        user = request.user
        if user.username is not 'admin' and not user.is_superuser:
            return Response('Only admin and superusers can view all accounts', status=status.HTTP_401_UNAUTHORIZED)

        all_users = AuthUser.objects.order_by('username')
        all_profiles = [user.get_profile() for user in all_users]
        serialized_data = ProfileSerializer(all_profiles).data
        response = Response(serialized_data)
        return response

class User(APIView):

    @api_auth_token_required
    def get(self, request, username):
        """
        Return the object belonging to the user as well as the 'default' provider/identity
        1. Test for authenticated username (Or if admin is the username for emulate functionality)
        2. <DEFAULT PROVIDER> Select first provider username can use
        3. <DEFAULT IDENTITY> Select first provider username can use
        4. Set in session THEN pass in response
        """
        user = request.user
        if user.username is not 'admin' or not user.is_superuser:
            return Response('Only admin and superusers can view individual account profiles', status=status.HTTP_401_UNAUTHORIZED)

        logger.info(request.__dict__)

        user = AuthUser.objects.get(username=username)
        serialized_data = ProfileSerializer(user.get_profile()).data
        response = Response(serialized_data)
        return response

    @api_auth_token_required
    def delete():
        """
        Remove the user belonging to the username.
        1. Test for authenticated
        2. Mark account as deleted (Don't delete?)
        """
        user = request.user
        if user.username is not 'admin' or not user.is_superuser:
            return Response('Only admin and superusers can delete individual account profiles', status=status.HTTP_401_UNAUTHORIZED)
        return Response('NotImplemented', status=status.HTTP_501_NOT_IMPLEMENTED)

    @api_auth_token_required
    def put():
        """
        Update user information
        (Should this be available? LDAP needs to take care of this
        """
        user = request.user
        if user.username is not 'admin' or not user.is_superuser:
            return Response('Only admin and superusers can update individual account profiles', status=status.HTTP_401_UNAUTHORIZED)
        return Response('NotImplemented', status=status.HTTP_501_NOT_IMPLEMENTED)
