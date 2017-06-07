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
from django.http import HttpResponse, HttpResponseRedirect
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
        qs = Instance.for_user(user)
        if 'archived' in self.request.query_params:
            return qs
        return qs.filter(only_current())

    def retrieve(self, request, pk=None):
        """
        Retrieve a signed token for a web desktop view.
        """
        instance_id = pk
        if not request.user.is_authenticated():
            logger.info("not authenticated: \nrequest:\n %s" % request)
            raise PermissionDenied

        logger.info("user is authenticated, well done.")
        instance = self.get_queryset().filter(provider_alias=instance_id).first()
        if not instance:
            logger.info("Instance %s not found" % instance_id)
            return failure_response(
                status.HTTP_404_NOT_FOUND,
                'Instance %s not found / no longer exists' % (instance_id,))
        ip_address = instance.ip_address
        logger.info("ip_address: %s" % ip_address)

        token = None
        client = self.request.query_params.get('client', 'vnc')
        payload = {
            'token': '',
            'token_url': '',
        }
        try:
            redirect = self.request.query_params.get('redirect', False)
            if client == 'guacamole':
                protocol = self.request.query_params.get('protocol', 'vnc')
                token, api_token_url = self.guacamole_token(request, ip_address, protocol, redirect)
            else:
                token = self.web_desktop_token(request, ip_address)
                proxy_password = 'display'
                api_token_url = '%s?token=%s&password=%s' % (
                    settings.WEB_DESKTOP['redirect']['PROXY_URL'],
                    token, proxy_password)
            payload['token'] = token
            payload['token_url'] = api_token_url
        except Exception as exc:
            payload['error'] = exc.message
            payload['status'] = 403
        if redirect:
            response = HttpResponseRedirect(api_token_url)
            if client == 'vnc':
                response.set_cookie('original_referer', request.META['HTTP_REFERER'],
                    domain=settings.WEB_DESKTOP['redirect']['COOKIE_DOMAIN'])
            logger.info("redirect response to %s", api_token_url)
            return response
        response = Response(payload)
        return response

    def guacamole_token(self, request, ip_address, protocol, redirect=False):
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
                          + '&id=' + conn_id)

        # SFTP is only enabled for SSH because when using SSH, the user enters their password,
        # while for a VNC connection, the user doesn't. On VNC connections this causes a connection
        # error because Guacamole cannot login to SFTP.
        if protocol == 'ssh':
            request_string += '&guac.enable-sftp=true'

        # Send request to Guacamole backend and record the result
        response = requests.post(guac_server + '/api/tokens', data=request_string)
        logger.info("Response status from server: %s" % (response.status_code))

        if response.status_code == 403:
            logger.warn("Guacamole did not accept the authentication.\nResponse content:\n%s" % (json.loads(response.content)))
            return HttpResponse(
                "<h1>Error 403</h1><br/>Guacamole server did not accept authentication.",
                status=403)

        token = json.loads(response.content)['authToken']
        api_token_url = guac_server + '/#/client/' + base64_conn_id + '?token=' + token
        return token, api_token_url

    def web_desktop_token(self, request, ip_address):
        # NOTE: Lets say you wanted an _extra level of security_
        #       if you need to 'tie in' to Atmosphere API, this code
        #       below would be helpful in phoning home for verification.
        # auth_token = request.session.get('token')
        # if not auth_token:
        #     auth_token = request.META['HTTP_AUTHORIZATION']
        # if not auth_token:
        #     return failure_response(
        #         status.HTTP_501_NOT_IMPLEMENTED,
        #         "Token could not be determined! If you can reproduce this, please file an issue!")
        # SIGNER = Signer(
        #     settings.WEB_DESKTOP['fingerprint']['SECRET_KEY'],
        #     salt=settings.WEB_DESKTOP['fingerprint']['SALT'])
        # token_fingerprint = SIGNER.get_signature(auth_token)

        signed_serializer = URLSafeTimedSerializer(
            settings.WEB_DESKTOP['signing']['SECRET_KEY'],
            salt=settings.WEB_DESKTOP['signing']['SALT'])

        token = signed_serializer.dumps([
            ip_address,
            # auth_token,
            # token_fingerprint,
            # settings.SERVER_URL,
            ])
        #Future-FIXME: Now that guacamole requires web_token & additional information for the redirect, should we return the api_token_url here, too?
        return token
