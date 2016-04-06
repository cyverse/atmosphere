from core.models import InstanceAction

from api.v2.serializers.details import InstanceActionSerializer
from api.v2.views.base import AuthReadOnlyViewSet


class InstanceActionViewSet(AuthReadOnlyViewSet):
    """
    API endpoint that allows instance actions to be viewed
    """
    queryset = InstanceAction.valid_actions.all()
    serializer_class = InstanceActionSerializer

# TODO: Remove actions that aren't available for public consumption
# Examples: Resize, Imaging, Terminate
