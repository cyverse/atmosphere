from rest_framework.response import Response
from api.v2.views.base import AuthViewSet
from rest_framework.settings import api_settings
from api.v2.serializers.details.allocation_source_command import AllocationSourceCommandSerializer



class AllocationSourceCommands:

    def __init__(self, name, desc):
        self.name = name
        self.desc = desc


#list of commands available

commands = {
    1: AllocationSourceCommands(
    name='create Allocation Source',
    desc='Create an Allocation Source'
    )

}

class AllocationSourceCommandViewSet(AuthViewSet):
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES
    serializer_class = AllocationSourceCommandSerializer

    def get_queryset(self):
        serializer = AllocationSourceCommandSerializer(
            instance = commands.values(), many=True
        )
        return Response(serializer.data)