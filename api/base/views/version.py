"""
Atmosphere api to lookup version info from git
"""
from os.path import join
from django.conf import settings
from rest_framework import viewsets, mixins
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from atmosphere.version import git_version_lookup
from api.permissions import InMaintenance


class VersionViewSet(mixins.ListModelMixin,
                     viewsets.GenericViewSet):
    permission_classes = (IsAuthenticatedOrReadOnly,
                          InMaintenance)

    git_directory = join(settings.PROJECT_ROOT, ".git")

    def list(self, request, *args, **kwargs):
        """
        This request will retrieve Atmosphere's version,
        including the latest update to the code base and the date the
        update was written.
        """
        version = git_version_lookup(git_directory=self.git_directory)
        return Response(version)


class DeployVersionViewSet(VersionViewSet):
    git_directory = join(settings.ANSIBLE_ROOT, ".git")
