from django.contrib.auth.models import AnonymousUser

from api.v2.serializers.details import AllocationSerializer
from api.v2.views.base import AuthViewSet
from api.v2.views.mixins import MultipleFieldLookup
from api.permissions import CloudAdminRequired
from api.pagination import OptionalPagination
from core.models import Allocation


class AllocationViewSet(MultipleFieldLookup, AuthViewSet):

    """
    API endpoint that allows providers to be viewed or edited.
    NOTE: we have *INTENTIONALLY* left out the ability to *UPDATE* or *DELETE* a allocation.
    This can have *disasterous cascade issues* on dependent models.
    DO NOT DELETE or UPDATE allocation objects!
    """
    lookup_fields = ("id", "uuid")
    queryset = Allocation.objects.all()
    serializer_class = AllocationSerializer
    permission_classes = (
        CloudAdminRequired,
    )
    pagination_class = OptionalPagination
    http_method_names = ['get', 'post', 'head', 'options', 'trace']
