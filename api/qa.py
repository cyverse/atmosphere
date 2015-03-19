"""
One-off class-views for QA to use/test the Atmosphere API instead of the DB
"""
 
from rest_framework.response import Response
from rest_framework.views import APIView

from api.permissions import ApiAuthRequired, ApiAuthOptional
from api.serializers import ProviderMachineSerializer

from core.models import ProviderMachine

class MachineNameLookup(APIView):
    """
    Given a machine_name, return all matching PMs
    """
    permission_classes = (ApiAuthOptional,)

    def get(self, request, machine_name):
        """
        """
        pms = ProviderMachine.objects.filter(application__name=machine_name)

        serialized_data = ProviderMachineSerializer(pms,
               request_user=None,
               many=True,
               ).data
        return Response(serialized_data)
