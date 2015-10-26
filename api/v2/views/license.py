from core.models import License
from api.v2.serializers.details import LicenseSerializer
from api.v2.views.base import AuthViewSet
from api.v2.views.mixins import MultipleFieldLookup

class LicenseViewSet(MultipleFieldLookup, AuthViewSet):

    """
    API endpoint that allows licenses to be viewed or edited.
    """

    queryset = License.objects.none()
    serializer_class = LicenseSerializer
    filter_fields = ('title',)
    search_fields = ('^title',)
    lookup_fields = ("id", "uuid")

    def get_queryset(self):
        """
        Filter out tags for deleted instances
        """
        user_id = self.request.user.id
        return License.objects.filter(created_by_id=user_id)
