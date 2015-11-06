from django.contrib.auth.models import AnonymousUser

from api.v2.serializers.details import QuotaSerializer
from api.v2.views.base import AuthViewSet
from api.v2.views.mixins import MultipleFieldLookup
from api.permissions import CanEditOrReadOnly
from core.models import Quota


class QuotaViewSet(MultipleFieldLookup, AuthViewSet):

    """
    API endpoint that allows providers to be viewed or edited.
    NOTE: we have *INTENTIONALLY* left out the ability to *UPDATE* or *DELETE* a quota.
    This can have *disasterous cascade issues* on other fields. DONT DELETE or UPDATE quota!
    """
    lookup_fields = ("id", "uuid")
    queryset = Quota.objects.all()
    serializer_class = QuotaSerializer
    permission_classes = (
        CanEditOrReadOnly,
    )
    http_method_names = ['get', 'post', 'head', 'options', 'trace']

    def get_queryset(self):
        """
        Filter allocations current user.
        """
        user = self.request.user
        if type(user) == AnonymousUser or not user.is_staff:
            return Quota.objects.none()
