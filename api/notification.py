"""
Atmosphere service notification rest api.

"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from threepio import logger

from core.email import send_instance_email
from core.models.instance import Instance as CoreInstance

from api import failure_response


class NotificationList(APIView):
    """
    Represents:
        A List of Instance
        Calls to the Instance Class
    """
    def _select_action(self, request, action, params):
        if 'instance_launched' in action:
            self._email_instance_owner(request, params)
        #elif '' in action:

    def _email_instance_owner(self, request, params):
        '''
        OLD API
        '''
        instance_token = params.get('token')
        username = params.get('userid')
        vm_info = params.get('vminfo')
        instance_name = params.get('name')
        instance = CoreInstance.objects.filter(provider_alias=vm_info['instance-id'])
        error_list = []
        if not instance:
            error_list.append(
                "The token %s did not match a core instance."
                 % instance_token)
            instance = CoreInstance.objects.filter(
                ip_address=request.META['REMOTE_ADDR'])
        if not instance:
            error_list.append(
                "The IP Address %s did not match a core instance."
                % request.META['REMOTE_ADDR'])
            return failure_response(
                status.HTTP_404_NOT_FOUND,
                str(error_list))
        instance = instance[0]
        ip_address = vm_info.get('public-ipv4',
                                 request.META.get('REMOTE_ADDR'))
        if ip_address:
            instance.ip_address = ip_address
            instance.save()
        launch_time = instance.start_date
        linuxusername = vm_info.get('linuxusername', instance.created_by)
        instance_id = vm_info.get('instance-id', instance.provider_alias)
        # Only send email if the provider isn't OpenStack.
        if instance.created_by_identity.provider.type.name != "OpenStack":
            send_instance_email(username, instance_id, instance_name,
                                ip_address, launch_time, linuxusername)

    def post(self, request):
        """
        Selects instance matching instance_token and
        POST a notification to the creator, dependent on the action
        TODO: Record launched activity in log/db for profiling later
        """
        params = request.DATA
        logger.info(request)
        logger.info(params)
        action = params.get('action', 'instance_launched')
        self._select_action(request, action, params)
        response = Response(status=status.HTTP_200_OK)
        return response
