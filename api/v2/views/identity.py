from rest_framework.decorators import detail_route
from rest_framework.response import Response
from rest_framework import status
from rest_framework import filters
import django_filters

from core.models import Identity, Group
from core.query import only_current_provider

from api.v2.serializers.details import IdentitySerializer
from api.v2.views.base import AuthModelViewSet
from api.v2.views.mixins import MultipleFieldLookup


class IdentityFilter(filters.FilterSet):
    project_id = django_filters.CharFilter('identity_memberships__member__projects__id')
    project_uuid = django_filters.CharFilter('identity_memberships__member__projects__uuid')
    group_id = django_filters.CharFilter('identity_memberships__member__id')

    class Meta:
        model = Identity
        fields = ["project_id", "project_uuid", "group_id"]


class IdentityViewSet(MultipleFieldLookup, AuthModelViewSet):
    """
    API endpoint that allows providers to be viewed or edited.
    """
    filter_class = IdentityFilter
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
        identity_list = Identity.shared_with_user(user).filter(only_current_provider())
        return identity_list
