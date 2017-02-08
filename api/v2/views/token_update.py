from django.contrib.auth.models import AnonymousUser

from core.models import Identity

from api.v2.serializers.post import TokenUpdateSerializer
from api.v2.views.base import AuthViewSet


class TokenUpdateViewSet(AuthViewSet):
    """
    API endpoint that allows providers to be viewed or edited.
    """
    lookup_fields = ("id", "uuid")
    queryset = Identity.objects.all()
    serializer_class = TokenUpdateSerializer
    http_method_names = ['post', 'head', 'options', 'trace']

    def get_queryset(self):
        """
        Filter providers by current user
        """
        user = self.request.user
        if (type(user) == AnonymousUser):
            return Identity.objects.none()

        identities = user.current_identities()
        return identities
