from api.v2.views.base import AuthModelViewSet
from api.v2.serializers.details import SSHKeySerializer

from core.models import SSHKey


class SSHKeyViewSet(AuthModelViewSet):

    """
    API endpoint that allows providers to be viewed or edited.
    """
    serializer_class = SSHKeySerializer
    def get_queryset(self):
        """
        Filter projects by current user
        """
        user = self.request.user
        return SSHKey.objects.filter(atmo_user=user)
