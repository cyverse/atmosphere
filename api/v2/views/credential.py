from django.contrib.auth.models import AnonymousUser

from api.v2.serializers.details import CredentialSerializer
from api.v2.views.base import AuthViewSet
from api.v2.views.mixins import MultipleFieldLookup
from api.permissions import CanEditOrReadOnly
from core.models import Credential


class CredentialViewSet(MultipleFieldLookup, AuthViewSet):

    """
    API endpoint that allows providers to be viewed or edited.
    NOTE: we have *INTENTIONALLY* left out the ability to *UPDATE* or *DELETE* a allocation.
    This can have *disasterous cascade issues* on other fields. DONT DELETE or UPDATE allocation!
    """
    lookup_fields = ("id", "uuid")
    queryset = Credential.objects.all()
    serializer_class = CredentialSerializer
    permission_classes = (
        CanEditOrReadOnly,
    )
    http_method_names = ['get', 'head', 'options', 'trace']

    def get_queryset(self):
        """
        Filter projects by current user.
        """
        user = self.request.user
        if type(user) == AnonymousUser:
            return Credential.objects.none()
        if user.is_staff and 'admin' in self.request.query_params:
            return Credential.objects.all()
        qs = Credential.objects.filter(identity__created_by=user)
        return qs
