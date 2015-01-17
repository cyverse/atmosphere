"""
atmosphere service post boot scripts rest api.

"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response


from core.models.group import Group
from core.models.post_boot import ScriptType, BootScript, get_scripts_for_user

from api import failure_response
from api.serializers import BootScriptSerializer
from api.permissions import ApiAuthRequired


class PostBootScriptList(APIView):
    """PostBootScripts represent a script to be deployed on an instance and/or
    application after Atmosphere has finished deploying the instance.
    PostBootScripts can be of type URL, Raw Text.
    """
    permission_classes = (ApiAuthRequired,)
    
    def get(self, request):
        """
        Authentication Required, list of PostBootScripts on your account.
        """
        username = request.user.username
        scripts = get_scripts_for_user(username)
        serialized_data = BootScriptSerializer(scripts, many=True).data
        return Response(serialized_data)

    def post(self, request):
        """
        Authentication Required, list of PostBootScripts on your account.
        """
        username = request.user.username
        data = request.DATA
        serializer = BootScriptSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return failure_response(
            status.HTTP_400_BAD_REQUEST,
            serializer.errors)


class PostBootScript(APIView):
    """PostBootScripts represent the different Cloud configurations hosted on Atmosphere.
    PostBootScripts can be of type AWS, Eucalyptus, OpenStack.
    """
    permission_classes = (ApiAuthRequired,)
    
    def get(self, request, script_id):
        """
        Authentication Required, return specific PostBootScript.
        """
        username = request.user.username
        scripts = get_scripts_for_user(username)
        try:
            script = scripts.get(id=script_id)
        except BootScript.DoesNotExist:
            return failure_response(
                status.HTTP_404_NOT_FOUND,
                "PostBootScript of id %s does not exist." % script_id)
        serialized_data = BootScriptSerializer(script).data
        return Response(serialized_data)
    def patch(self, request, script_id):
        return self._update_script(request, script_id)
    def put(self, request, script_id):
        return self._update_script(request, script_id)
    def _update_script(self, request, script_id):
        user = request.user
        data = request.DATA
        partial = True if request.method == 'PATCH' else False
        #Step 1: Retrieve or 'Forbidden' on updating script
        scripts = get_scripts_for_user(user.username)

        try:
            script = scripts.get(id=script_id)
        except BootScript.DoesNotExist:
            return failure_response(
                status.HTTP_404_NOT_FOUND,
                "PostBootScript of id %s does not exist." % script_id)
        serializer = BootScriptSerializer(script, data=data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return failure_response(
            status.HTTP_400_BAD_REQUEST,
            serializer.errors)



