from rest_framework import viewsets
from core.models import ProviderMachine
from api.v2.serializers.details import ProviderMachineSerializer


class ProviderMachineViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows instance actions to be viewed or edited.
    """
    queryset = ProviderMachine.objects.all()
    serializer_class = ProviderMachineSerializer
