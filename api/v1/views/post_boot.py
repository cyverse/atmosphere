"""
atmosphere service post boot scripts rest api.

"""
from rest_framework import status
from rest_framework.response import Response

from core.models.group import Group
from core.models.boot_script import ScriptType, BootScript,\
    get_scripts_for_user

from api import failure_response
from api.v1.serializers import BootScriptSerializer
from api.v1.views.base import AuthAPIView


class BootScriptList(AuthAPIView):

    """
    BootScripts represent a script to be deployed on an instance and/or
    application after Atmosphere has finished deploying the instance.
    BootScripts can be of type URL or Raw Text.
    """

    def get(self, request):
        """
        Authentication Required, list of BootScripts on your account.
        """
        username = request.user.username
        scripts = get_scripts_for_user(username)
        serialized_data = BootScriptSerializer(scripts, many=True).data
        return Response(serialized_data)

    def post(self, request):
        """
        Authentication Required, list of BootScripts on your account.
        """
        username = request.user.username
        data = request.data
        serializer = BootScriptSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return failure_response(
            status.HTTP_400_BAD_REQUEST,
            serializer.errors)


class BootScript(AuthAPIView):

    """
    BootScripts represent the different Cloud configurations hosted
    on Atmosphere.
    BootScripts can be of type AWS, Eucalyptus, OpenStack.
    """

    def get(self, request, script_id):
        """
        Authentication Required, return specific BootScript.
        """
        username = request.user.username
        scripts = get_scripts_for_user(username)
        try:
            script = scripts.get(id=script_id)
        except CoreBootScript.DoesNotExist:
            return failure_response(
                status.HTTP_404_NOT_FOUND,
                "BootScript of id %s does not exist." % script_id)
        serialized_data = BootScriptSerializer(script).data
        return Response(serialized_data)

    def patch(self, request, script_id):
        return self._update_script(request, script_id)

    def put(self, request, script_id):
        return self._update_script(request, script_id)

    def _update_script(self, request, script_id):
        user = request.user
        data = request.data
        partial = True if request.method == 'PATCH' else False
        # Step 1: Retrieve or 'Forbidden' on updating script
        scripts = get_scripts_for_user(user.username)
        try:
            script = scripts.get(id=script_id)
        except CoreBootScript.DoesNotExist:
            return failure_response(
                status.HTTP_404_NOT_FOUND,
                "BootScript of id %s does not exist." % script_id)
        serializer = BootScriptSerializer(script, data=data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return failure_response(
            status.HTTP_400_BAD_REQUEST,
            serializer.errors)
