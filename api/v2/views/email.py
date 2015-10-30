"""
 RESTful Email API
"""

from django.conf import settings

from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework import status

from api import permissions
from api.v2.exceptions import failure_response
from core.email import email_admin, feedback_email, resource_request_email


class EmailViewSet(ViewSet):
    permission_classes = (permissions.ApiAuthRequired,)
    required_keys = []

    def create(self, *args, **kwargs):
        user = self.request.user
        data = self.request.data
        missing_keys = self.check_missing_keys(data, self.required_keys)
        if missing_keys:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                "Missing required POST data variables : %s" % missing_keys)
        # Inject SERVER_URL settings
        data['server'] = settings.SERVER_URL
        result = self._email(user, data)
        return result

    def check_missing_keys(self, data, required_keys):
        """
        Return any missing required post key names.
        """
        return [key for key in required_keys
                # Key must exist and have a non-empty value.
                if key not in data or
                (isinstance(data[key], str) and len(data[key]) > 0)]

    def _email(self, user, data):
        raise NotImplemented("This function to be implemented by the subclass")


class SupportEmailViewSet(EmailViewSet):
    required_keys = ["message", "subject", "user-interface"]

    def _email(self, user, data):
        subject = data.pop('subject')
        message = data.pop('message')
        email_success = email_admin(
            self.request, subject, message, data=data)
        email_response = {"email_sent": email_success}
        if not email_success:
            return Response(email_response, status=status.HTTP_400_BAD_REQUEST)
        return Response(email_response, status=status.HTTP_200_OK)


class FeedbackEmailViewSet(EmailViewSet):
    required_keys = ["message", "user-interface"]

    def _email(self, user, data):
        message = data.pop('message')
        email_response = feedback_email(
            self.request, user.username, user.email, message, data)
        if email_response.get('result', {}).get('code', 'failed') == 'failed':
            return Response(email_response, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(email_response, status=status.HTTP_200_OK)


class ResourceEmailViewSet(EmailViewSet):
    required_keys = ["quota", "reason"]

    def _email(self, user, data):
        quota = data.pop('quota')
        reason = data.pop('reason')
        email_response = resource_request_email(
            self.request, user.username, quota, reason)
        if not email_response.get('email_sent', False):
            return Response(email_response, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(email_response, status=status.HTTP_200_OK)
