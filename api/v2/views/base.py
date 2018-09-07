from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet, ViewSet

from api.permissions import (
        ApiAuthOptional, ApiAuthRequired, EnabledUserRequired, InMaintenance,
        CloudAdminRequired, ProjectLeaderRequired,
        UserListAdminQueryable
    )


class AuthViewSet(ViewSet):
    http_method_names = ['get', 'put', 'patch', 'post',
                         'delete', 'head', 'options', 'trace']
    permission_classes = (InMaintenance,
                          EnabledUserRequired,
                          ApiAuthRequired,
                          ProjectLeaderRequired)


class AuthModelViewSet(ModelViewSet):
    http_method_names = ['get', 'put', 'patch', 'post',
                         'delete', 'head', 'options', 'trace']
    permission_classes = (InMaintenance,
                          EnabledUserRequired,
                          ApiAuthRequired,)


class AdminViewSet(AuthViewSet):
    permission_classes = (InMaintenance,
                          CloudAdminRequired,
                          EnabledUserRequired,
                          ApiAuthRequired,)


class AdminModelViewSet(AuthModelViewSet):
    permission_classes = (InMaintenance,
                          CloudAdminRequired,
                          EnabledUserRequired,
                          ApiAuthRequired,)


class UserListAdminQueryAndUpdate():
    permission_classes = (InMaintenance,
                          EnabledUserRequired,
                          ApiAuthRequired,
                          UserListAdminQueryable)


class AuthOptionalViewSet(ModelViewSet):

    permission_classes = (InMaintenance,
                          ApiAuthOptional,)


class AuthReadOnlyViewSet(ReadOnlyModelViewSet):

    permission_classes = (InMaintenance,
                          ApiAuthOptional,)


class OwnerUpdateViewSet(AuthModelViewSet):
    """
    Base class ViewSet to handle the case where a normal user should see 'GET'
    and an owner (or admin) should be allowed to PUT or PATCH
    """

    http_method_names = ['get', 'put', 'patch', 'post',
                         'delete', 'head', 'options', 'trace']

    @property
    def allowed_methods(self):
        raise Exception("The @property-method 'allowed_methods' should be"
                        " handled by the subclass of OwnerUpdateViewSet")
