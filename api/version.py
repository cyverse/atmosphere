"""
Atmosphere API version service.

"""
from rest_framework.views import APIView
from rest_framework.response import Response

from atmosphere.version import get_version


class Version(APIView):
    def get(self, request, format=None):
        """
        This request will retrieve Atmosphere's version,
        including the latest update to the code base and the date the update was written.
        """
        return Response(get_version("all"))
