"""
Atmosphere API Common/Base views.

"""
from rest_framework import viewsets, mixins
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from atmosphere.version import get_version
try:
    from atmosphere_ansible_bioci.version import get_version as get_deploy_version
except ImportError:
    get_deploy_version = None

from api.permissions import InMaintenance


class VersionViewSet(mixins.ListModelMixin,
                     viewsets.GenericViewSet):
    permission_classes = (IsAuthenticatedOrReadOnly,
                          InMaintenance)

    def list(self, request, *args, **kwargs):
        """
        This request will retrieve Atmosphere's version,
        including the latest update to the code base and the date the
        update was written.
        """
        return Response(get_version("all"))


class DeployVersionViewSet(mixins.ListModelMixin,
                           viewsets.GenericViewSet):
    permission_classes = (IsAuthenticatedOrReadOnly,
                          InMaintenance)

    def list(self, request, format=None):
        """
        This request will retrieve Atmosphere's version,
        including the latest update to the code base and the date the
        update was written.
        """
        if not get_deploy_version:
            return Response("N/A")
        return Response(get_deploy_version("all"))
