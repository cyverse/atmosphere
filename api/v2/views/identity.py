from rest_framework import viewsets
from core.models import Identity, Group
from api.v2.serializers.details import IdentitySerializer
from core.query import only_current_provider


class IdentityViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows providers to be viewed or edited.
    """
    queryset = Identity.objects.all()
    serializer_class = IdentitySerializer
    http_method_names = ['get', 'head', 'options', 'trace']

    def get_queryset(self):
        """
        Filter identities by current user
        """
        user = self.request.user
        group = Group.objects.get(name=user.username)
        identities = group.identities.filter(only_current_provider(), provider__active=True)
        return identities
