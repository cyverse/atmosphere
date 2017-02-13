"""
Atmosphere service user rest api.

"""
from rest_framework.response import Response
from rest_framework import status

from threepio import logger

from atmosphere.settings import secrets
from django_cyverse_auth.models import create_token

from core.models import AtmosphereUser

from service.accounts.eucalyptus import AccountDriver

from api.v1.serializers import ProfileSerializer
from api.v1.views.base import AuthAPIView


class TokenEmulate(AuthAPIView):

    """
    This API allows already-authenticated users
    to request a new token that will emulate a user that is not their own.
    Due to the obvious security concerns, only 'staff' accounts or tokens
    owned by an administrator will be allowed.
    """

    def get(self, request, username):
        """
        Create a new token in the database on behalf of 'username'
        Returns success 201 Created - Body is JSON and contains
        """
        params = request.data
        user = request.user
        if not username:
            return Response("Username was not provided",
                            status=status.HTTP_400_BAD_REQUEST)
        if user.username is not 'admin' and not user.is_superuser:
            logger.error("URGENT! User: %s is attempting to emulate a user!"
                         % user.username)
            return Response("Only admin and superusers can emulate accounts. "
                            "This offense has been reported",
                            status=status.HTTP_401_UNAUTHORIZED)
        if not AtmosphereUser.objects.filter(username=username):
            return Response("Username %s does not exist as an AtmosphereUser"
                            % username, status=status.HTTP_404_NOT_FOUND)

        # User is authenticated, username exists. Make a token for them.
        token = create_token(username, issuer="DRF-EmulatedUser")
        expireTime = token.issuedTime + secrets.TOKEN_EXPIRY_TIME
        auth_json = {
            # Extra data passed only on emulation..
            "emulator": request.user.username,
            # Normal token data..
            "token": token.key,
            "username": token.user.username,
            "expires": expireTime.strftime("%b %d, %Y %H:%M:%S")
        }
        return Response(auth_json, status=status.HTTP_201_CREATED)
