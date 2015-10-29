from api import permissions
from api.v2.serializers.details import LicenseSerializer
from api.v2.views.base import AuthViewSet
from api.v2.views.mixins import MultipleFieldLookup
from core.models import License


class LicenseViewSet(MultipleFieldLookup, AuthViewSet):

    """
    API endpoint that allows licenses to be viewed or edited.
    """

    queryset = License.objects.none()
    permission_classes = (permissions.CanEditOrReadOnly,)
    serializer_class = LicenseSerializer
    filter_fields = ('title',)
    search_fields = ('^title',)
    lookup_fields = ("id", "uuid")

    def get_queryset(self):
        """
        Filter out tags for deleted instances
        """
        user_id = self.request.user.id
        qs = License.objects.all()
        if 'created' in self.request.query_params:
            qs = qs.filter(created_by_id=user_id)
        return qs
