from django_cyverse_auth.models import Token
from core.query import only_current_tokens

from api.permissions import ApiAuthRequired, InMaintenance
from api.v2.serializers.details import TokenSerializer
from api.v2.views.base import AuthOptionalViewSet
from api.v2.views.mixins import MultipleFieldLookup


class TokenViewSet(MultipleFieldLookup, AuthOptionalViewSet):

    """
    API endpoint that allows tags to be viewed or edited.
    """
    lookup_field = 'key'
    lookup_value_regex = "[^/]+"
    lookup_fields = ("key",)
    queryset = Token.objects.all()
    serializer_class = TokenSerializer
    permission_classes = (ApiAuthRequired,
                          InMaintenance,)

    def get_queryset(self):
        """
        Filter projects by current user.
        """
        user = self.request.user
        qs = Token.objects.filter(user=user)
        if 'archived' in self.request.query_params:
            return qs
        # Return current results
        return qs.filter(only_current_tokens())
