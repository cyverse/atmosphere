"""
 RESTful Email API
"""

from django.conf import settings
from django.template.loader import render_to_string
from django.template import Context

from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework import status

from api import permissions
from api.v2.exceptions import failure_response

from core.email import lookupEmail, resource_request_email, support_email, email_admin, request_data
from core.models import AtmosphereUser as User
from core.models import Instance, Volume

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


class VolumeSupportEmailViewSet(EmailViewSet):
    required_keys = ["message", "volume"]

    def _email(self, user, data):
        """
        Sends an instance/volume report email to support

        Returns a response.
        """
        subject = "Volume Instance Report from %s" % user.username;
        volume = Volume.objects \
                .filter(id=data["volume"])[0]

        context = {
            "problems": data.get("problems", []),
            "ui": data.get("user-interface", ""),
            "server": settings.SERVER_URL,
            "message": data["message"],
            "provider": user.selected_identity.provider,
            "volume": volume,
        }

        context.update(request_data(self.request))

        message = render_to_string("volume_report.html", context=context)
        email_success = email_admin(self.request, subject, message, 
                request_tracker=True)
        email_response = {"email_sent": email_success}
        if not email_success:
            return Response(email_response, status=status.HTTP_400_BAD_REQUEST)
        return Response(email_response, status=status.HTTP_200_OK)

class InstanceSupportEmailViewSet(EmailViewSet):
    required_keys = ["message", "instance"]

    def _email(self, user, data):
        """
        Sends an instance/volume report email to support

        Returns a response.
        """
        subject = "Atmosphere Instance Report from %s" % user.username;
        instance = Instance.objects.filter(id=data["instance"])[0]
        last_status = instance.instancestatushistory_set \
                              .order_by('start_date')  \
                              .last()

        context = {
            "problems": data.get("problems", []),
            "ui": data.get("user-interface", ""),
            "server": settings.SERVER_URL,
            "message": data["message"],
            "provider": user.selected_identity.provider,
            "instance": instance,
            "status": last_status
        }

        context.update(request_data(self.request))

        message = render_to_string("instance_report.html", context=context)
        email_success = email_admin(self.request, subject, message,
                request_tracker=True) 
        email_response = {"email_sent": email_success}
        if not email_success:
            return Response(email_response, status=status.HTTP_400_BAD_REQUEST)
        return Response(email_response, status=status.HTTP_200_OK)

class FeedbackEmailViewSet(EmailViewSet):
    required_keys = ["message"]

    def _email(self, user, data):
        """
        Sends an email to support based on feedback from a client machine

        Returns a response.
        """
        username = user.username
        subject = 'Subject: Atmosphere Client Feedback from %s' % username

        instances = Instance.objects \
            .filter(created_by=user.id) \
            .filter(end_date__exact=None)

        volumes = Volume.objects \
            .filter(instance_source__created_by__username=username) \
            .filter(instance_source__end_date__isnull=True)

        context = {
            "ui": data.get("user-interface", ""),
            "server": settings.SERVER_URL,
            "feedback": data["message"],
            "provider": user.selected_identity.provider,
            "instances": instances,
            "volumes": volumes,
        }

        context.update(request_data(self.request))

        body = render_to_string("feedback.html", context=context)
        email_success = email_admin(self.request, subject, body, 
                request_tracker=True)
        if email_success:
            resp_status = status.HTTP_200_OK
            email_response = {'result':
                    {'code': 'success',
                        'meta': '',
                        'value': (
                            'Thank you for your feedback! '
                            'Support has been notified.')}}
        else:
            resp_status = status.HTTP_400_BAD_REQUEST
            email_response = {'result':
                    {'code': 'failed',
                     'meta': '',
                     'value': 'Failed to send feedback!'}}
        return Response(email_response, status=resp_status)


class ResourceEmailViewSet(EmailViewSet):
    required_keys = ["quota", "reason"]

    def _email(self, user, data):
        email_response = resource_request_email(
            self.request, user.username, data["quota"], data["reason"])
        if email_response.get('email_sent', False):
            return Response(email_response, status=status.HTTP_200_OK)
        else:
            return Response(email_response, status=status.HTTP_400_BAD_REQUEST)
