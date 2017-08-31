import logging
import uuid
import json
import time
import hmac
import hashlib
import base64
import requests
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from itsdangerous import URLSafeTimedSerializer
from rest_framework import status
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response

from core.models import Instance
from core.query import only_current
from api.v2.exceptions import failure_response

logger = logging.getLogger(__name__)


class WebTokenView(RetrieveAPIView):

    def get_queryset(self):
        user = self.request.user
        qs = Instance.shared_with_user(user)
        if 'archived' in self.request.query_params:
            return qs
        return qs.filter(only_current())

    def retrieve(self, request, pk=None):
        """
        Retrieve a signed token for a web desktop view.
        """
        if not request.user.is_authenticated():
            raise PermissionDenied

        client = request.query_params.get('client')
        valid_guac = client == "guacamole" and settings.GUACAMOLE_ENABLED
        valid_webdesktop = client == "web_desktop"
        if not (valid_guac or valid_webdesktop):
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                'Invalid or missing "client" query paramater')

        instance = self.get_queryset().filter(provider_alias=pk).first()
        if not instance:
            return failure_response(
                status.HTTP_404_NOT_FOUND,
                'Instance %s not found / no longer exists' % pk)

        token = None
        token_url = None
        try:
            if client == 'guacamole':
                token, token_url = self.guacamole_token(instance.ip_address)
            else:
                token, token_url = self.web_desktop_token(instance.ip_address)
        except:
            logger.exception("Atmosphere failed to retrieve web token")
            return HttpResponse(
                "Atmosphere failed to retrieve web token",
                status=500)

        return Response({
            'token': token,
            'token_url': token_url
        })

    def guacamole_token(self, ip_address):
        request = self.request
        protocol = request.query_params.get('protocol', 'vnc')
        guac_server = settings.GUACAMOLE['SERVER_URL']
        guac_secret = settings.GUACAMOLE['SECRET_KEY']
        # Create UUID for connection ID
        conn_id = str(uuid.uuid4())
        base64_conn_id = base64.b64encode(conn_id[2:] + "\0" + 'c' + "\0" + 'hmac')

        # Create timestamp that looks like: 1489181545018
        timestamp = str(int(round(time.time()*1000)))

        # Get IP, protocol, and username from request that was sent from button click
        atmo_username = request.user.username

        logger.info("User %s initiated %s connection to %s" % (atmo_username, protocol.upper(), ip_address))

        # Change some parameters depending on SSH or VNC protocol
        # Note: passwd is hardcoded to 'display'. This doesn't seem ideal but it is
        #       done the same in web_desktop.py
        port = '5905'
        passwd = 'display'
        if protocol == 'ssh':
            port = '22'
            passwd = ''

        # Concatenate info for a message
        message = timestamp + protocol + ip_address + port + atmo_username + passwd

        # Hash the message into a signature
        signature = hmac.new(guac_secret, message, hashlib.sha256).digest().encode("base64").rstrip('\n')

        # Build the POST request
        request_string = ('timestamp=' + timestamp
                          + '&guac.port=' + port
                          + '&guac.username=' + atmo_username
                          + '&guac.password=' + passwd
                          + '&guac.protocol=' + protocol
                          + '&signature=' + signature
                          + '&guac.hostname=' + ip_address
                          + '&id=' + conn_id
                          + '&guac.sftp-username=' + atmo_username
                          + '&guac.sftp-directory=/home/' + atmo_username
                          + '&guac.enable-sftp=true')

        if protocol == "ssh":
            request_string += "&guac.color-scheme=white-black"

        # Send request to Guacamole backend and record the result
        response = requests.post(guac_server + '/api/tokens', data=request_string)
        logger.info("Response status from server: %s" % (response.status_code))

        # Raise exceptions for HTTP errors
        response.raise_for_status()

        token = json.loads(response.content)['authToken']
        token_url = guac_server + '/#/client/' + base64_conn_id + '?token=' + token
        return token, token_url

    def web_desktop_token(self, ip_address):
        signed_serializer = URLSafeTimedSerializer(
            settings.WEB_DESKTOP['signing']['SECRET_KEY'],
            salt=settings.WEB_DESKTOP['signing']['SALT'])

        token = signed_serializer.dumps([ip_address])

        token_url = '%s?token=%s&password=display' % \
            (settings.WEB_DESKTOP['redirect']['PROXY_URL'], token)

        return token, token_url
