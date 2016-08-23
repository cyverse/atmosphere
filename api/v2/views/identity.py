from rest_framework.decorators import detail_route
from rest_framework.response import Response
from rest_framework import status

from core.models import Identity, Group

from api.v2.serializers.details import IdentitySerializer
from api.v2.views.base import AuthViewSet
from api.v2.views.mixins import MultipleFieldLookup


class IdentityViewSet(MultipleFieldLookup, AuthViewSet):

    """
    API endpoint that allows providers to be viewed or edited.
    """
    lookup_fields = ("id", "uuid")
    queryset = Identity.objects.all()
    http_method_names = ['get', 'head', 'options', 'trace']

    @detail_route(methods=['GET'])
    def export(self, request, pk=None):
        """
        Until a better method comes about, we will handle InstanceActions here.
        """
        if type(pk) == int:
            kwargs = {"id": pk}
        else:
            kwargs = {"uuid": pk}
        identity = Identity.objects.get(**kwargs)
        export_data = identity.export()
        return Response(
            export_data,
            status=status.HTTP_200_OK)

    def get_serializer_class(self):
        serializer_class = IdentitySerializer
        if self.action == 'openrc':
            return serializer_class
        return serializer_class

    def get_queryset(self):
        """
        Filter identities by current user
        """
        user = self.request.user
        try:
            group = Group.objects.get(name=user.username)
        except Group.DoesNotExist:
            return Identity.objects.none()
        identities = group.current_identities.all()
        return identities
