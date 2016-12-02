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


#FIXME: Might want this to just be 'views/command.py' and CommandViewSet
class AllocationSourceCommandViewSet(AuthViewSet):
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES
    serializer_class = AllocationSourceCommandSerializer

    def list(self, request):
        #FIXME: List all the commands that can be executed here
        return Response()

    def create(self, request):
        #FIXME: Introspect the request.data and see if you can act on a command
        #FIXME: Return a structured JSON for each command so that the UI knows what to expect.
        return Response()
