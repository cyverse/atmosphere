"""
Atmosphere api email
"""
from rest_framework.response import Response
from rest_framework import status
from django.template.loader import render_to_string
from django.template import Context

from threepio import logger

from django_cyverse_auth.protocol.ldap import lookupEmail

from core.models import AtmosphereUser as User
from core.email import email_admin, resource_request_email

from api import failure_response
from api.v1.views.base import AuthAPIView


class Feedback(AuthAPIView):

    """
    Post feedback via RESTful API
    """

    def post(self, request):
        """
        Creates a new feedback email and sends it to admins.
        """
        required = ["message", "user-interface"]
        missing_keys = check_missing_keys(request.data, required)
        if missing_keys:
            return keys_not_found(missing_keys)
        result = self._email(request,
                             request.user.username,
                             lookupEmail(request.user.username),
                             request.data["message"])
        return Response(result, status=status.HTTP_201_CREATED)

    def _email(self, request, username, user_email, message):
        """
        Sends an email to support based on feedback from a client machine

        Returns a response.
        """
        user = User.objects.get(username=username)
        subject = 'Subject: Atmosphere Client Feedback from %s' % username
        context = {
            "user": user,
            "feedback": message
        }
        body = render_to_string("core/email/feedback.html",
                                context=Context(context))
        email_success = email_admin(request, subject, body, request_tracker=True)
        if email_success:
            resp = {'result':
                    {'code': 'success',
                        'meta': '',
                        'value': (
                            'Thank you for your feedback! '
                            'Support has been notified.')}}
        else:
            resp = {'result':
                    {'code': 'failed',
                     'meta': '',
                     'value': 'Failed to send feedback!'}}
        return resp


class QuotaEmail(AuthAPIView):

    """
    Post Quota Email via RESTful API.
    """

    def post(self, request):
        """
        Creates a new Quota Request email and sends it to admins.
        """
        required = ["quota", "reason"]
        missing_keys = check_missing_keys(request.data, required)
        if missing_keys:
            return keys_not_found(missing_keys)
        logger.debug("request.data = %s" % (str(request.data)))
        result = self._email(request,
                             request.user.username,
                             request.data["quota"],
                             request.data["reason"])
        return Response(result, status=status.HTTP_201_CREATED)

    def _email(self, request, username, new_resource, reason):
        """
        Processes resource request increases. Sends email to the admins

        Returns a response.
        """
        return resource_request_email(request, username, new_resource, reason)


class SupportEmail(AuthAPIView):

    def post(self, request):
        """
        Creates a new support email and sends it to admins.

        Post Support Email via RESTful API
        """
        required = ["message", "subject","user-interface"]
        missing_keys = check_missing_keys(request.data, required)
        if missing_keys:
            return keys_not_found(missing_keys)
        result = self._email(request,
                             request.data["subject"],
                             request.data["message"])
        return Response(result, status=status.HTTP_201_CREATED)

    def _email(self, request, subject, message):
        """
        Sends an email to support.

        POST Params expected:
        * user
        * message
        * subject

        Returns a response.
        """
        email_success = email_admin(request, subject, message, request_tracker=True)
        return {"email_sent": email_success}


def check_missing_keys(data, required_keys):
    """
    Return any missing required post key names.
    """
    return [key for key in required_keys
            # Key must exist and have a non-empty value.
            if key not in data or
            (isinstance(data[key], str) and len(data[key]) > 0)]


def keys_not_found(missing_keys):
    return failure_response(
        status.HTTP_400_BAD_REQUEST,
        "Missing required POST data variables : %s" % missing_keys)
