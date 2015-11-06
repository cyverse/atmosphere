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
    serializer_class = IdentitySerializer
    http_method_names = ['get', 'head', 'options', 'trace']

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
