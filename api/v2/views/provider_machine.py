from core.models import ProviderMachine

from api.v2.serializers.details import ProviderMachineSerializer
from api.v2.views.base import AuthReadOnlyViewSet


class ProviderMachineViewSet(AuthReadOnlyViewSet):
    """
    API endpoint that allows instance actions to be viewed or edited.
    """

    queryset = ProviderMachine.objects.all()
    serializer_class = ProviderMachineSerializer
