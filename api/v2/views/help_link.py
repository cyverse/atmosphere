"""
Help Links API
"""
from django.shortcuts import get_object_or_404

from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework import status

from core.models import HelpLink
from api import permissions
from api.v2.serializers.details import HelpLinkSerializer
from api.v2.views.base import AuthOptionalViewSet


class HelpLinkViewSet(AuthOptionalViewSet):

    """
    API endpoint that allows scripts to be viewed or edited.
    """
    # Admins can Update a HelpLink, users can only see it.
    permission_classes = (permissions.IsAdminOrReadOnly,)
    serializer_class = HelpLinkSerializer
    queryset = HelpLink.objects.all()
    http_method_names = ['get', 'head', 'options', 'trace']
