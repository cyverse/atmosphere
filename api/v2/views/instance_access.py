from core.models import InstanceAccess, StatusType
from core.query import only_current
from core.events.serializers.instance_access import RemoveInstanceAccessSerializer

from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from api.v2.exceptions import failure_response
from api.v2.views.base import AuthModelViewSet
from api.v2.serializers.details import (
    InstanceAccessSerializer,
    UserInstanceAccessSerializer
)


class InstanceAccessViewSet(AuthModelViewSet):

    """
    API endpoint that will show all InstanceAccess involving the request user.
    """

    queryset = InstanceAccess.objects.all()
    serializer_class = UserInstanceAccessSerializer
    admin_serializer_class = InstanceAccessSerializer
    filter_fields = ('instance__provider_alias', 'user__username', 'user__id')

    def destroy(self, request, pk=None):
        request_user = request.user
        instance_access = self.queryset.get(pk=pk)
        origin_user = instance_access.instance.created_by
        dest_user = instance_access.user
        if request_user != origin_user and request_user != dest_user:
            return failure_response(
                status.HTTP_403_FORBIDDEN,
                "You are not allowed to delete this access request.")
        if instance_access.status.name == "approved":
            serializer = RemoveInstanceAccessSerializer(data={
                'user': instance_access.user.username,
                'instance': instance_access.instance.provider_alias
            })
            if not serializer.is_valid():
                errors = serializer.errors
                return failure_response(
                    status.HTTP_400_BAD_REQUEST,
                    "Error occurred while removing instance_access for "
                    "Instance:%s, Username:%s -- %s"
                    % (
                        instance_access.instance,
                        instance_access.user,
                        errors))
            serializer.save()
        return super(InstanceAccessViewSet, self).destroy(request, pk=pk)

    def get_queryset(self):
        """
        Filter projects by current user.
        """
        user = self.request.user
        qs = InstanceAccess.shared_with_user(user.username)
        if 'archived' not in self.request.query_params:
            qs = qs.filter(only_current(end_date="instance__end_date"))
        return qs

    def get_serializer_class(self):
        """
        Return the `serializer_class` or `admin_serializer_class`
        given the users privileges.
        """
        assert self.admin_serializer_class is not None, (
            "%s should include an `admin_serializer_class` attribute."
            % self.__class__.__name__
        )
        http_method = self.request._request.method
        if http_method != 'POST' and self.request.user.is_staff:
            return self.admin_serializer_class
        return self.serializer_class
