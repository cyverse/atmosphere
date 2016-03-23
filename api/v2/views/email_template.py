"""
Email Template API
"""
from django.shortcuts import get_object_or_404

from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework import status

from core.models import EmailTemplate
from api import permissions
from api.v2.serializers.details import EmailTemplateSerializer


class EmailTemplateViewSet(ViewSet):

    """
    API endpoint that allows scripts to be viewed or edited.
    """
    permission_classes = (permissions.ApiAuthRequired,)
    serializer_class = EmailTemplateSerializer
    queryset = EmailTemplate.objects.all()

    def list(self, request):
        return self.retrieve(1)

    def retrieve(self, request, pk=None):
        template = get_object_or_404(self.queryset, pk=1)
        serializer = self.serializer_class(template)
        return Response(serializer.data)

    def update(self, request, pk=None):
        return self.partial_update(request, pk)

    def partial_update(self, request, pk=None):
        template = get_object_or_404(self.queryset, pk=1)
        serializer = self.serializer_class(template, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        else:
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)
