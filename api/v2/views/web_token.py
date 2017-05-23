import logging

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseRedirect
from django.http.request import UnreadablePostError
from django.shortcuts import render, redirect, render_to_response
from django.template import RequestContext

from itsdangerous import Signer, URLSafeTimedSerializer

from rest_framework import status
from rest_framework import exceptions as rest_exceptions
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response
from rest_framework import authentication, permissions, mixins
from core.models import Instance
from core.query import only_current

from api.v2.exceptions import failure_response

logger = logging.getLogger(__name__)


SIGNED_SERIALIZER = URLSafeTimedSerializer(
    settings.WEB_DESKTOP['signing']['SECRET_KEY'],
    salt=settings.WEB_DESKTOP['signing']['SALT'])

SIGNER = Signer(
    settings.WEB_DESKTOP['fingerprint']['SECRET_KEY'],
    salt=settings.WEB_DESKTOP['fingerprint']['SALT'])


class WebTokenView(RetrieveAPIView):

    def get_queryset(self):
        user = self.request.user
        qs = Instance.for_user(user)
        if 'archived' in self.request.query_params:
            return qs
        return qs.filter(only_current())

    def retrieve(self, request, pk=None):
        return self.web_desktop(request, pk)

    def web_desktop(self, request, instance_id):
        """
        Signs a redirect to transparent proxy for web desktop view.
        """
        template_params = {}

        logger.info("POST body: %s" % request.POST)
        if not request.user.is_authenticated():
            logger.info("not authenticated: \nrequest:\n %s" % request)
            raise PermissionDenied

        logger.info("user is authenticated, well done.")
        sig = None
        instance = self.get_queryset().filter(provider_alias=instance_id).first()
        if not instance:
            logger.info("Instance %s not found" % instance_id)
            return failure_response(
                status.HTTP_404_NOT_FOUND,
                'Instance %s no longer exists' % (instance_id,))
        ip_address = instance.ip_address
        auth_token = request.session.get('token')

        logger.info("ip_address: %s" % ip_address)
        token_fingerprint = SIGNER.get_signature(auth_token)

        sig = SIGNED_SERIALIZER.dumps([ip_address,
            token_fingerprint])

        payload = {
            'token': sig,
        }
        response = Response(payload)
        return response

