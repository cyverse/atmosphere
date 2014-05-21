"""
Atmosphere service instance rest api.

"""
## Frameworks
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.reverse import reverse

from threepio import logger
## Atmosphere Libraries


from api.permissions import InMaintenance, ApiAuthRequired
from api.serializers import ProjectSerializer


class Project(APIView):
    """
    """
    
    permission_classes = (ApiAuthRequired,)
    
    def get(self, request):
        """
        """
        user = request.user
        serialized_data = ProjectSerializer([user], many=True, context={"request":request}).data
        response = Response(serialized_data)
        return response
