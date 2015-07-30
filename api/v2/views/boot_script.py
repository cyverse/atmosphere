from core.models import BootScript
from api.v2.serializers.details import BootScriptSerializer
from api.v2.views.base import AuthViewSet

class BootScriptViewSet(AuthViewSet):

    """
    API endpoint that allows scripts to be viewed or edited.
    """

    queryset = BootScript.objects.none()
    serializer_class = BootScriptSerializer
    filter_fields = ('title',)
    search_fields = ('^title',)

    def get_queryset(self):
        """
        Filter out tags for deleted instances
        """
        user_id = self.request.user.id
        return BootScript.objects.filter(created_by_id=user_id)
