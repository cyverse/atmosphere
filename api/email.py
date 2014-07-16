"""
Atmosphere api email
"""
from django.core import urlresolvers

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from threepio import logger

from authentication.protocol.ldap import lookupEmail

from core.email import email_admin
from core.models.group import IdentityMembership
from core.models.user import AtmosphereUser as User

from api import failure_response
from api.permissions import ApiAuthRequired


class Feedback(APIView):
    """
    Post feedback via RESTful API
    """

    permission_classes = (ApiAuthRequired,)

    def post(self, request):
        """
        Creates a new feedback email and sends it to admins.
        """
        required = ["message"]
        missing_keys = check_missing_keys(request.DATA, required)
        if missing_keys:
            return keys_not_found(missing_keys)
        result = self._email(request,
                             request.user.username,
                             lookupEmail(request.user.username),
                             request.DATA["message"])
        return Response(result, status=status.HTTP_201_CREATED)

    def _email(self, request, username, user_email, message):
        """
        Sends an email Bto support based on feedback from a client machine

        Returns a response.
        """
        subject = "Subject: Atmosphere Client Feedback from %s" % username
        message = "---\nFeedback: %s\n---" % message
        email_success = email_admin(request, subject, message)
        if email_success:
            resp = {"result":
                    {"code": "success",
                     "meta": "",
                     "value": "Thank you for your feedback! "
                     + "Support has been notified."}}
        else:
            resp = {"result":
                    {"code": "failed",
                     "meta": "",
                     "value": "Failed to send feedback!"}}
        return resp


class QuotaEmail(APIView):
    """
    Post Quota Email via RESTful API
    """

    permission_classes = (ApiAuthRequired,)

    def post(self, request):
        """
        Creates a new Quota Request email and sends it to admins
        """
        required = ["quota", "reason"]
        missing_keys = check_missing_keys(request.DATA, required)
        if missing_keys:
            return keys_not_found(missing_keys)
        logger.debug("request.DATA = %s" % (str(request.DATA)))
        result = self._email(request,
                             request.user.username,
                             request.DATA["quota"],
                             request.DATA["reason"])
        return Response(result, status=status.HTTP_201_CREATED)

    def _email(self, request, username, new_quota, reason):
        """
        Processes Increase Quota request. Sends email to atmo@iplantc.org

        Returns a response.
        """
        user = User.objects.get(username=username)
        membership = IdentityMembership.objects.get(
            identity=user.select_identity(),
            member__in=user.group_set.all())
        admin_url = urlresolvers.reverse(
            "admin:core_identitymembership_change",
            args=(membership.id,))
        message = """
        Username : %s
        Quota Requested: %s
        Reason for Quota Increase: %s
        URL for Quota Increase:%s
        """ % (username, new_quota, reason,
               request.build_absolute_uri(admin_url))
        subject = "Atmosphere Quota Request - %s" % username
        logger.info(message)
        email_success = email_admin(request, subject, message, cc_user=False)
        return {"email_sent": email_success}


class SupportEmail(APIView):
    """
    """

    permission_classes = (ApiAuthRequired,)

    def post(self, request):
        """
        Creates a new support email and sends it to admins.

        Post Support Email via RESTful API
        """
        required = ["message", "subject"]
        missing_keys = check_missing_keys(request.DATA, required)
        if missing_keys:
            return keys_not_found(missing_keys)
        result = self._email(request,
                             request.DATA["subject"],
                             request.DATA["message"])
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
        email_success = email_admin(request, subject, message)
        return {"email_sent": email_success}


def check_missing_keys(data, required_keys):
    """
    Return any missing required post key names.
    """
    return [key for key in required_keys
            #Key must exist and have a non-empty value.
            if key not in data
            or (type(data[key]) == str and len(data[key]) > 0)]


def keys_not_found(missing_keys):
    return failure_response(
        status.HTTP_400_BAD_REQUEST,
        "Missing required POST data variables : %s" % missing_keys)
