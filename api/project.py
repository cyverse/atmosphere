"""
Atmosphere service instance rest api.

"""
## Frameworks
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.reverse import reverse

from threepio import logger
## Atmosphere Libraries

from authentication.decorators import api_auth_token_required

from api.serializers import ProjectSerializer


class Project(APIView):
    """
    """

    @api_auth_token_required
    def get(self, request):
        """
        """
        user = request.user
        serialized_data = ProjectSerializer([user], many=True, context={"request":request}).data
        response = Response(serialized_data)
        return response
