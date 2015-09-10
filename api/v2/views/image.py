from django.contrib.auth.models import AnonymousUser

from core.models import Application as Image
from core.models import AtmosphereUser, AccountProvider
from core.query import only_current, only_current_apps

from api import permissions
from api.v2.serializers.details import ImageSerializer
from api.v2.views.base import AuthOptionalViewSet
from api.v2.views.mixins import MultipleFieldLookup


class ImageViewSet(MultipleFieldLookup, AuthOptionalViewSet):

    """
    API endpoint that allows images to be viewed or edited.
    """
    lookup_fields = ("id", "uuid")

    http_method_names = ['get', 'put', 'patch', 'head', 'options', 'trace']

    filter_fields = ('created_by__username', 'tags__name')

    permission_classes = (permissions.InMaintenance,
                          permissions.ApiAuthOptional,
                          permissions.CanEditOrReadOnly,
                          permissions.ApplicationMemberOrReadOnly)

    serializer_class = ImageSerializer

    search_fields = ('id', 'name', 'versions__change_log', 'tags__name',
                     'tags__description', 'created_by__username')

    def get_queryset(self):
        request_user = self.request.user
        return Image.current_apps(request_user)
