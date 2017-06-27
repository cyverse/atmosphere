from rest_framework.decorators import detail_route
from rest_framework.response import Response
from rest_framework import status
from rest_framework import filters
import django_filters

from core.models import Identity, Group, Quota, AtmosphereUser
from core.query import only_current_provider

from api.v2.serializers.details import (IdentitySerializer)
from api.v2.views.base import AuthModelViewSet
from api.v2.views.mixins import MultipleFieldLookup
from api.exceptions import failure_response


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
    serializer_class = IdentitySerializer
    queryset = Identity.objects.all()
    http_method_names = ['get', 'head', 'options', 'trace', 'patch']

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

    def queryset_by_username(self, username):
        try:
            group = Group.objects.get(name=username)
        except Group.DoesNotExist:
            return Identity.objects.none()
        identities = group.current_identities.all()
        return identities

    def get_queryset(self):
        """
        Filter identities by current user
        """
        user = self.request.user
        idents = Identity.shared_with_user(user)
        if user.is_admin():
            if 'all_users' in self.request.GET:
                idents = Identity.objects.all()
            if 'username' in self.request.GET:
                target_username = self.request.GET.get('username')
                user = AtmosphereUser.objects.get(username=target_username)
                idents = Identity.shared_with_user(user)

        return idents.filter(only_current_provider())

    def get_serializer_class(self):
        return IdentitySerializer

    def update(self, request, pk=None, partial=False):
        data = request.data
        if not request.user.is_admin():
            return failure_response(
                status.HTTP_403_FORBIDDEN,
                "Non-admin users cannot update an Identity")
        if not pk:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                "Key required to update identity")
        if 'quota' not in data:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                "Only 'quota' can be updated on identity")

        identity = Identity.objects.get(uuid=pk)
        SerializerCls = self.get_serializer_class()
        serializer = SerializerCls(
            identity, data=data,
            context={'request': self.request})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
                serializer.data,
                status=status.HTTP_202_ACCEPTED)
