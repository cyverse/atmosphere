"""
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from core.models import Application

from api.permissions import InMaintenance
from api.serializers import ApplicationSerializer


class ApplicationListNoAuth(APIView):
    """
    Represents:
        A Manager of Machine
        Calls to the Machine Class
    TODO: POST when we have programmatic image creation/snapshots
    """

    permission_classes = (InMaintenance,)
    # NOTE-ABLY ABSENT.. API AUTH NOT REQUIRED FOR THIS LINE
    #@api_auth_token_required
    def get(self, request):
        """
        Using provider and identity, getlist of machines
        TODO: Cache this request
        """
        applications = Application.objects.filter(private=False)
        serialized_data = ApplicationSerializer(applications,
                                                many=True).data
        response = Response(serialized_data)
        return response
