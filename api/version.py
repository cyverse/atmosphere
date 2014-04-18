"""
Atmosphere API version service.

"""
from rest_framework.views import APIView
from rest_framework.response import Response

from atmosphere.version import get_version


class Version(APIView):
    def get(self, request, format=None):
        """
        Atmosphere's version
        """
        return Response(get_version("all"))
