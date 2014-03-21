"""
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from core.models import Application
from core.models.application import visible_applications, public_applications

from authentication.decorators import api_auth_token_optional
from api.permissions import InMaintenance
from api.serializers import ApplicationSerializer


class ApplicationList(APIView):
    """
    Represents:
        A Manager of Machine
        Calls to the Machine Class
    TODO: POST when we have programmatic image creation/snapshots
    """

    permission_classes = (InMaintenance,)

    @api_auth_token_optional
    def get(self, request, **kwargs):
        """
        Using provider and identity, getlist of machines
        TODO: Cache this request
        """
        request_user = kwargs.get('request_user')
        applications = public_applications()
        #Concatenate 'visible'
        if request_user:
            my_apps = visible_applications(request_user)
            applications.extend(my_apps)
        serialized_data = ApplicationSerializer(applications,
                                                many=True).data
        response = Response(serialized_data)
        return response
