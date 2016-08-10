import django_filters

from core.models import AllocationSource, UserAllocationSource
from api.v2.serializers.details import AllocationSourceSerializer
from api.v2.views.base import AuthViewSet
from api.v2.views.mixins import MultipleFieldLookup


class AllocationSourceViewSet(MultipleFieldLookup, AuthViewSet):

    """
    API endpoint that allows scripts to be viewed or edited.
    """

    queryset = AllocationSource.objects.none()
    serializer_class = AllocationSourceSerializer
    search_fields = ('^title',)
    lookup_fields = ('id', 'uuid')
    http_method_names = ['options','head','get']

    def get_queryset(self):
        """
        Filter out tags for deleted instances
        """
        user = self.request.user
        return AllocationSource.for_user(user)
