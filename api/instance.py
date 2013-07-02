"""
Atmosphere service instance rest api.
"""
from datetime import datetime
import time

from django.contrib.auth.models import User

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from libcloud.common.types import InvalidCredsError

from threepio import logger

from authentication.decorators import api_auth_token_required

from core.models.instance import convertEshInstance, update_instance_metadata
from core.models.volume import convertEshVolume

from api import failureJSON, launchEshInstance, prepareDriver
from api.serializers import InstanceSerializer, VolumeSerializer

from service import task

class InstanceList(APIView):
    """
    Represents:
        A Manager of Instance
        Calls to the Instance Class
    """
    @api_auth_token_required
    def get(self, request, provider_id, identity_id):
        """
        Returns a list of all instances
        """
        method_params = {}
        user = request.user
        esh_driver = prepareDriver(request, identity_id)

        try:
            esh_instance_list = esh_driver.list_instances(method_params)
        except InvalidCredsError:
            logger.exception(
                'Authentication Failed. Provider-id:%s Identity-id:%s'
                % (provider_id, identity_id))
            errorObj = failureJSON([{
                'code': 401,
                'message': 'Identity/Provider Authentication Failed'}])
            return Response(errorObj, status=status.HTTP_401_UNAUTHORIZED)

        core_instance_list = [convertEshInstance(esh_driver, inst, provider_id, user)
                              for inst in esh_instance_list]

        #TODO: Core/Auth checks for shared instances

        serialized_data = InstanceSerializer(core_instance_list, many=True).data
        response = Response(serialized_data)
        response['Cache-Control'] = 'no-cache'
        return response

    @api_auth_token_required
    def post(self, request, provider_id, identity_id, format=None):
        """
        Instance Class:
        Launches an instance based on the params
        Returns a single instance

        Parameters: machine_alias, size_alias, username

        TODO: Create a 'reverse' using the instance-id to pass
        the URL for the newly created instance
        I.e: url = "/provider/1/instance/1/i-12345678"
        """
        data = request.DATA
        user = request.user
        esh_driver = prepareDriver(request, identity_id)
        try:
            (esh_instance, token) = launchEshInstance(esh_driver, data)
        except InvalidCredsError:
            logger.warn(
                'Authentication Failed. Provider-id:%s Identity-id:%s'
                % (provider_id, identity_id))
            errorObj = failureJSON([{
                'code': 401,
                'message': 'Identity/Provider Authentication Failed'}])
            return Response(errorObj, status=status.HTTP_401_UNAUTHORIZED)

        core_instance = convertEshInstance(
            esh_driver, esh_instance, provider_id, user, token)
        serializer = InstanceSerializer(core_instance, data=data)
        #NEVER WRONG
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class InstanceHistory(APIView):
    """
    An InstanceHistory provides instance history for an identity.

    GET - A chronologically ordered list of Instances.
    """
    
    @api_auth_token_required
    def get(self, request, provider_id, identity_id):
        data = request.DATA
        user = User.objects.filter(username=request.user)
        if user:
            user = user[0]
        else:
            errorObj = failureJSON([{
                'code': 401,
                'message': 'User not found'}])
            return Response(errorObj, status=status.HTTP_401_UNAUTHORIZED)
        
        # Active Instances
        esh_driver = prepareDriver(request, identity_id)
        esh_instance_list = esh_driver.list_instances()
        active_instance_list = [convertEshInstance(esh_driver, inst, provider_id, user)
                              for inst in esh_instance_list]

        # Historic Instances
        history_instance_list = Instance.objects.filter(created_by=user.id)
        merged_instance_list = dict(history_instance_list.items()
                                    + active_instance_list.items())
        # fix [:20]!
        serialized_data = InstanceSerializer(merged_instance_list[:20], many=True).data
        response = Response(serialized_data)
        response['Cache-Control'] = 'no-cache'
        return response

class InstanceAction(APIView):
    """
    An InstanceAction allows users to:

    TODO:Find a list of available actions for an instance.

    GET - None

    POST - Run specified action
    """

    @api_auth_token_required
    def post(self, request, provider_id, identity_id, instance_id):
        """
        """
        #Service-specific call to action
        action_params = request.DATA
        user = request.user
        if not action_params.get('action', None):
            errorObj = failureJSON([{
                'code': 400,
                'message':
                'POST request to /action require a BODY with \'action\':'}])
            return Response(errorObj, status=status.HTTP_400_BAD_REQUEST)
        esh_driver = prepareDriver(request, identity_id)
        esh_instance = esh_driver.get_instance(instance_id)
        try:
            action = action_params['action']
            result_obj = None
            if 'volume' in action:
                volume_id = action_params.get('volume_id')
                esh_volume = esh_driver.get_volume(volume_id)
                device = action_params.get('device', None)
                if 'attach_volume' == action:
                    esh_driver.attach_volume(
                        esh_instance,
                        esh_volume,
                        device)
                elif 'detach_volume' == action:
                    esh_driver.detach_volume(esh_volume)
                #If attaching, wait until we leave the intermediary state...
                attempts = 0
                while True:
                    esh_volume = esh_driver.get_volume(volume_id)
                    core_volume = convertEshVolume(esh_volume, provider_id, user)
                    result_obj = VolumeSerializer(core_volume).data
                    logger.debug(result_obj)
                    if attempts >= 6:  # After 6 attempts (~1min)
                        break
                    if 'attaching' not in esh_volume.extra['status']\
                            and 'detaching' not in esh_volume.extra['status']:
                        break
                    time.sleep(2**attempts)  # Exponential backoff..
                    attempts += 1
                logger.debug(
                    "%s completed in %s attempts"
                    % (action, attempts))
                if esh_volume.extra['status'] == 'available':
                    errorObj = failureJSON([{
                        'code': 503,
                        'message': 'Volume attachment failed. Please try again'}])
                    return Response(
                        errorObj,
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)
            elif 'resize' == action:
                size_alias = action_params.get('size_alias', '')
                size = esh_driver.get_size(size_alias)
                esh_driver.resize_instance(esh_instance, size)
            elif 'confirm_resize' == action:
                esh_driver.confirm_resize_instance(esh_instance)
            elif 'revert_resize' == action:
                esh_driver.revert_resize_instance(esh_instance)
            elif 'resume' == action:
                esh_driver.resume_instance(esh_instance)
            elif 'suspend' == action:
                esh_driver.suspend_instance(esh_instance)
            elif 'start' == action:
                esh_driver.start_instance(esh_instance)
            elif 'stop' == action:
                esh_driver.stop_instance(esh_instance)
            elif 'reboot' == action:
                esh_driver.reboot_instance(esh_instance)
            elif 'rebuild' == action:
                machine_alias = action_params.get('machine_alias', '')
                machine = esh_driver.get_machine(machine_alias)
                esh_driver.rebuild_instance(esh_instance, machine)
            else:
                errorObj = failureJSON([{
                    'code': 400,
                    'message': 'Unable to to perform action %s.' % (action)}])
                return Response(
                    errorObj,
                    status=status.HTTP_400_BAD_REQUEST)
            api_response = {
                'result': 'success',
                'message': 'The requested action <%s> was run successfully'
                % action_params['action'],
                'object': result_obj,
            }
            response = Response(api_response, status=status.HTTP_200_OK)
            return response
        except InvalidCredsError:
            logger.warn(
                'Authentication Failed. Provider-id:%s Identity-id:%s'
                % (provider_id, identity_id))
            errorObj = failureJSON([{
                'code': 401,
                'message': 'Identity/Provider Authentication Failed'}])
            return Response(errorObj, status=status.HTTP_401_UNAUTHORIZED)
        except NotImplemented, ne:
            logger.exception(ne)
            errorObj = failureJSON([{
                'code': 404,
                'message':
                'The requested action %s is not available on this provider'
                % action_params['action']}])
            return Response(errorObj, status=status.HTTP_404_NOT_FOUND)


class Instance(APIView):
    """
    An instance is a self-contained copy
    of a machine built to a specific size and hosted on a specific provider
    """
    #renderer_classes = (JSONRenderer, JSONPRenderer)

    @api_auth_token_required
    def get(self, request, provider_id, identity_id, instance_id):
        """
        Return the object belonging to this instance ID
        TODO: Filter out instances you shouldnt see (permissions..)
        """
        user = request.user
        esh_driver = prepareDriver(request, identity_id)

        try:
            esh_instance = esh_driver.get_instance(instance_id)
        except InvalidCredsError:
            logger.warn(
                'Authentication Failed. Provider-id:%s Identity-id:%s'
                % (provider_id, identity_id))
            errorObj = failureJSON([{
                'code': 401,
                'message': 'Identity/Provider Authentication Failed'}])
            return Response(errorObj, status=status.HTTP_401_UNAUTHORIZED)

        if not esh_instance:
            return instance_not_found(instance_id)

        core_instance = convertEshInstance(esh_driver, esh_instance,
                                           provider_id, user)
        serialized_data = InstanceSerializer(core_instance).data
        response = Response(serialized_data)
        response['Cache-Control'] = 'no-cache'
        return response

    @api_auth_token_required
    def patch(self, request, provider_id, identity_id, instance_id):
        """
        """
        user = request.user
        data = request.DATA
        #Ensure item exists on the server first
        esh_driver = prepareDriver(request, identity_id)
        try:
            esh_instance = esh_driver.get_instance(instance_id)
        except InvalidCredsError:
            logger.warn(
                'Authentication Failed. Provider-id:%s Identity-id:%s'
                % (provider_id, identity_id))
            errorObj = failureJSON([{
                'code': 401,
                'message': 'Identity/Provider Authentication Failed'}])
            return Response(errorObj, status=status.HTTP_400_BAD_REQUEST)

        if not esh_instance:
            return instance_not_found(instance_id)

        #Gather the DB related item and update
        core_instance = convertEshInstance(esh_driver, esh_instance,
                                           provider_id, user)
        serializer = InstanceSerializer(core_instance, data=data, partial=True)
        if serializer.is_valid():
            logger.info('metadata = %s' % data)
            update_instance_metadata(esh_driver, esh_instance, data)
            serializer.save()
            response = Response(serializer.data)
            logger.info('data = %s' % serializer.data)
            response['Cache-Control'] = 'no-cache'
            return response
        else:
            return Response(
                    serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST)

    @api_auth_token_required
    def put(self, request, provider_id, identity_id, instance_id):
        """
        TODO:
            Options for put
            - Instance status change (suspend,resume,etc.)
            - DB changes (Name, tags)
        """
        user = request.user
        data = request.DATA
        #Ensure item exists on the server first
        esh_driver = prepareDriver(request, identity_id)
        try:
            esh_instance = esh_driver.get_instance(instance_id)
        except InvalidCredsError:
            logger.warn(
                'Authentication Failed. Provider-id:%s Identity-id:%s'
                % (provider_id, identity_id))
            errorObj = failureJSON([{
                'code': 401,
                'message': 'Identity/Provider Authentication Failed'}])
            return Response(errorObj, status=status.HTTP_400_BAD_REQUEST)

        if not esh_instance:
            return instance_not_found(instance_id)

        #Gather the DB related item and update
        core_instance = convertEshInstance(esh_driver, esh_instance,
                                           provider_id, user)
        serializer = InstanceSerializer(core_instance, data=data)
        if serializer.is_valid():
            logger.info('metadata = %s' % data)
            update_instance_metadata(esh_driver, esh_instance, data)
            serializer.save()
            response = Response(serializer.data)
            logger.info('data = %s' % serializer.data)
            response['Cache-Control'] = 'no-cache'
            return response
        else:
            return Response(serializer.errors, status=400)

    @api_auth_token_required
    def delete(self, request, provider_id, identity_id, instance_id):
        user = request.user
        esh_driver = prepareDriver(request, identity_id)

        try:
            esh_instance = esh_driver.get_instance(instance_id)
            if not esh_instance:
                return instance_not_found(instance_id)
            task.destroy_instance_task(esh_driver, esh_instance)
            esh_instance = esh_driver.get_instance(instance_id)
            if esh_instance.extra\
               and 'task' not in esh_instance.extra:
                esh_instance.extra['task'] = 'queueing delete'
            core_instance = convertEshInstance(esh_driver, esh_instance, provider_id, user)
            if core_instance:
                core_instance.end_date = datetime.now()
                core_instance.save()
            serialized_data = InstanceSerializer(core_instance).data
            response = Response(serialized_data, status=200)
            response['Cache-Control'] = 'no-cache'
            return response
        except InvalidCredsError:
            logger.warn(
                'Authentication Failed. Provider-id:%s Identity-id:%s'
                % (provider_id, identity_id))
            errorObj = failureJSON([{
                'code': 401,
                'message': 'Identity/Provider Authentication Failed'}])
            return Response(errorObj, status=status.HTTP_400_BAD_REQUEST)

def instance_not_found(instance_id):
    errorObj = failureJSON([{
        'code': 404,
        'message': 'Instance %s does not exist' % instance_id}])
    return Response(errorObj, status=status.HTTP_404_NOT_FOUND)
