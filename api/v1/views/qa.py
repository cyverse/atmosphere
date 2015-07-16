"""
One-off class-views for QA to use/test the Atmosphere API instead of the DB
"""
from rest_framework.response import Response

from core.models import ProviderMachine

from api.v1.serializers import ProviderMachineSerializer
from api.v1.views.base import AuthOptionalAPIView


class MachineNameLookup(AuthOptionalAPIView):

    """
    Given a machine_name, return all matching PMs
    """

    def get(self, request, machine_name):
        pms = ProviderMachine.objects.filter(application__name=machine_name)
        serialized_data = ProviderMachineSerializer(pms,
                                                    request_user=None,
                                                    many=True).data
        return Response(serialized_data)
