"""
 Allow staff users to emulate users by spawning a token
"""

from django.conf import settings
from django.utils import timezone
from django.http import HttpResponseRedirect
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework import status
from uuid import uuid4
from api import permissions
from api.v2.serializers.details import TokenSerializer
from django_cyverse_auth.models import create_token
from atmosphere.settings import secrets
from core.models import AtmosphereUser
from threepio import logger


class TokenEmulateViewSet(ViewSet):
    lookup_field = 'username'
    permission_classes = (permissions.IsAdminOrReadOnly,)
    required_keys = []

    def retrieve(self, *args, **kwargs):
        user = self.request.user
        # data = self.request.data
        username = kwargs.get('username')
        expireDate = timezone.now() + secrets.TOKEN_EXPIRY_TIME
        new_token = create_token(
                username,
                token_key='EMULATED-'+str(uuid4()),
                remote_ip=self.request.META['REMOTE_ADDR'],
                token_expire=expireDate,
                issuer="DRF-EmulatedToken-%s" % user.username)
        serialized_data = TokenSerializer(new_token, context={'request':self.request}).data
        return Response(serialized_data, status=status.HTTP_201_CREATED)


class SessionEmulateViewSet(TokenEmulateViewSet):
    def retrieve(self, *args, **kwargs):
        user = self.request.user
        # data = self.request.data
        username = kwargs.get('username')
        if username == user.username:
            # This will clear the emulation
            username = None
        response = emulate_session(self.request, username)
        return response


def emulate_session(request, username=None):
    try:
        logger.info("Emulate attempt: %s wants to be %s"
                    % (request.user, username))
        logger.info(request.session.__dict__)
        if not username and 'emulator' in request.session:
            logger.info("Clearing emulation attributes from user")
            request.session['username'] = request.session['emulator']
            del request.session['emulator']
            # Allow user to fall through on line below

        try:
            user = AtmosphereUser.objects.get(username=username)
        except AtmosphereUser.DoesNotExist:
            logger.info("Emulate attempt failed. User <%s> does not exist"
                        % username)
            return HttpResponseRedirect(
                settings.REDIRECT_URL +
                "/api/v2")

        logger.info("Emulate success, creating tokens for %s" % username)
        expireDate = timezone.now() + secrets.TOKEN_EXPIRY_TIME
        token = create_token(
            username,
            token_key='EMULATED-'+str(uuid4()),
            token_expire=expireDate,
            remote_ip=request.META['REMOTE_ADDR'],
            issuer="DRF-EmulatedSession-%s" % user.username)
        token.save()
        # Keep original emulator if it exists, or use the last known username
        original_emulator = request.session.get(
            'emulator', request.session['username'])
        request.session['emulator'] = original_emulator
        # Set the username to the user to be emulated
        # to whom the token also belongs
        request.session['username'] = username
        request.session['token'] = token.key
        logger.info("Returning emulated user - %s - to api root "
                    % username)
        logger.info(request.session.__dict__)
        logger.info(request.user)
        serialized_data = TokenSerializer(token, context={'request': request}).data
        return Response(serialized_data, status=status.HTTP_201_CREATED)
    except Exception as e:
        logger.warn("Emulate request failed")
        logger.exception(e)
        return HttpResponseRedirect(settings.REDIRECT_URL + "/api/v2")
