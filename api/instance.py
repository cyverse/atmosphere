"""
Atmosphere service instance rest api.
"""
from datetime import datetime
import time

from django.contrib.auth.models import User
from django.core.paginator import Paginator,\
    PageNotAnInteger, EmptyPage

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from libcloud.common.types import InvalidCredsError

from threepio import logger

from authentication.decorators import api_auth_token_required

from core.models.instance import convert_esh_instance, update_instance_metadata
from core.models.instance import Instance as CoreInstance

from core.models.size import convert_esh_size

from core.models.volume import convert_esh_volume

from api import failureJSON, launch_esh_instance, prepare_driver
from api.serializers import InstanceSerializer, VolumeSerializer,\
    PaginatedInstanceSerializer

from service import task
from service.deploy import build_script
from service.quota import check_over_quota
from service.allocation import check_over_allocation, print_timedelta

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
        esh_driver = prepare_driver(request, identity_id)

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

        core_instance_list = [convert_esh_instance(esh_driver,
                                                 inst,
                                                 provider_id,
                                                 identity_id,
                                                 user)
                              for inst in esh_instance_list]

        #[core_instance.update_history(
        #    core_instance.esh.extra['status'],
        #    core_instance.esh.extra.get('task') or\
        #    core_instance.esh.extra.get('metadata',{}).get('tmp_status'))
        # for core_instance in core_instance_list]

        #TODO: Core/Auth checks for shared instances

        serialized_data = InstanceSerializer(core_instance_list,
                                             many=True).data
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
        esh_driver = prepare_driver(request, identity_id)
        size_alias = data.get('size_alias', '')

        try:
            size = esh_driver.get_size(size_alias)

            #TEST 1 - Over on resouces
            if check_over_quota(request.user.username, identity_id, size):
                errorObj = failureJSON([{
                    'code': 403,
                    'message': 'Exceeds resource quota'}])
                return Response(errorObj, status=status.HTTP_401_UNAUTHORIZED)
            #TEST 2 - Over on time ( and by how much)
            over_allocation, time_diff = check_over_allocation(
                    request.user.username,
                    identity_id)
            if over_allocation:
                errorObj = failureJSON([{
                    'code': 403,
                    'message': 'Exceeds time allocation. Wait %s before launching'
                               'instance' % print_timedelta(time_diff)}])
                return Response(errorObj, status=status.HTTP_403_FORBIDDEN)
            #TEST 3 - size is unavailable
            core_size = convert_esh_size(size, provider_id, user)
            if not core_size.active():
                errorObj = failureJSON([{
                    'code': 403,
                    'message': 'Size not available.'}])
                return Response(errorObj, status=status.HTTP_403_FORBIDDEN)
            #ASSERT: OK To Launch
            (esh_instance, token) = launch_esh_instance(esh_driver, data)
        except InvalidCredsError:
            logger.warn(
                'Authentication Failed. Provider-id:%s Identity-id:%s'
                % (provider_id, identity_id))
            errorObj = failureJSON([{
                'code': 401,
                'message': 'Identity/Provider Authentication Failed'}])
            return Response(errorObj, status=status.HTTP_401_UNAUTHORIZED)

        core_instance = convert_esh_instance(
            esh_driver, esh_instance, provider_id, identity_id, user, token)
        core_instance.update_history(
            core_instance.esh.extra['status'],
            core_instance.esh.extra.get('task') or\
            core_instance.esh.extra.get('metadata',{}).get('tmp_status'),
            first_update=True)
        logger.info("Statushistory updated")
        serializer = InstanceSerializer(core_instance, data=data)
        #NEVER WRONG
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)


class InstanceHistory(APIView):
    """
    An InstanceHistory provides instance history for an identity.

    GET - A chronologically ordered list of Instances.
    """

    @api_auth_token_required
    def get(self, request, provider_id, identity_id):
        data = request.DATA
        user = User.objects.filter(username=request.user)

        if user and len(user) > 0:
            user = user[0]
        else:
            errorObj = failureJSON([{
                'code': 401,
                'message': 'User not found'}])
            return Response(errorObj, status=status.HTTP_401_UNAUTHORIZED)

        esh_driver = prepare_driver(request, identity_id)

        # Historic Instances in reverse chronological order
        history_instance_list = CoreInstance.objects.filter(
            created_by=user.id).order_by("-start_date")

        page = request.QUERY_PARAMS.get('page')
        if page:
            paginator = Paginator(history_instance_list, 5)
            try:
                history_instance_page = paginator.page(page)
            except PageNotAnInteger:
                # If page is not an integer, deliver first page.
                history_instance_page = paginator.page(1)
            except EmptyPage:
                # Page is out of range.
                # deliver last page of results.
                history_instance_page = paginator.page(paginator.num_pages)
            serialized_data = \
                PaginatedInstanceSerializer(
                    history_instance_page).data
        else:
            serialized_data = InstanceSerializer(history_instance_list,
                                                 many=True).data

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
        esh_driver = prepare_driver(request, identity_id)
        esh_instance = esh_driver.get_instance(instance_id)
        try:
            action = action_params['action']
            result_obj = None
            update_status = False
            if 'volume' in action:
                volume_id = action_params.get('volume_id')
                if 'attach_volume' == action:
                    #TODO: Make this async again by changing our volume
                    # workflow
                    mount_location = action_params.get('mount_location',None)
                    device = action_params.get('device', None)
                    task.attach_volume_task(esh_driver, esh_instance.alias,
                                            volume_id, device, mount_location)
                elif 'detach_volume' == action:
                    (result, error_msg) = \
                        task.detach_volume_task(
                            esh_driver, esh_instance.alias,
                            volume_id)
                    if not result and error_msg:
                        errorObj = failureJSON([{
                            'code': 400,
                            'message': error_msg}])
                        return Response(
                            errorObj,
                            status=status.HTTP_400_BAD_REQUEST)

                #Task complete, convert the volume and return the object
                esh_volume = esh_driver.get_volume(volume_id)
                core_volume = convert_esh_volume(esh_volume,
                                               provider_id,
                                               identity_id,
                                               user)
                result_obj = VolumeSerializer(core_volume).data
                logger.debug(result_obj)
            elif 'resize' == action:
                size_alias = action_params.get('size_alias', '')
                size = esh_driver.get_size(size_alias)
                esh_driver.resize_instance(esh_instance, size)
            elif 'confirm_resize' == action:
                esh_driver.confirm_resize_instance(esh_instance)
            elif 'revert_resize' == action:
                esh_driver.revert_resize_instance(esh_instance)
            elif 'resume' == action:
                if check_over_quota(request.user.username,
                                   identity_id,
                                   esh_instance.size):
                    errorObj = failureJSON([{
                        'code': 403,
                        'message': 'Exceeds resource quota'}])
                    return Response(errorObj, status=status.HTTP_403_FORBIDDEN)
                over_allocation, time_diff = check_over_allocation(
                        request.user.username,
                        identity_id)
                if over_allocation:
                    errorObj = failureJSON([{
                        'code': 403,
                        'message': 'Exceeds time allocation. Wait %s before'
                                   'resuming instance' % print_timedelta(time_diff)
                        }])
                    return Response(errorObj, status=status.HTTP_403_FORBIDDEN)
                update_status = True
                esh_driver.resume_instance(esh_instance)
            elif 'suspend' == action:
                update_status = True
                esh_driver.suspend_instance(esh_instance)
            elif 'start' == action:
                update_status = True
                esh_driver.start_instance(esh_instance)
            elif 'stop' == action:
                update_status = True
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
            if update_status:
                esh_instance = esh_driver.get_instance(instance_id)
                core_instance = convert_esh_instance(esh_driver,
                                                   esh_instance,
                                                   provider_id,
                                                   identity_id,
                                                   user)
                core_instance.update_history(
                    core_instance.esh.extra['status'],
                    core_instance.esh.extra.get('task'))
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
        esh_driver = prepare_driver(request, identity_id)

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

        core_instance = convert_esh_instance(esh_driver, esh_instance,
                                           provider_id, identity_id, user)

        #core_instance.update_history(core_instance.esh.extra['status'],
        #                             core_instance.esh.extra.get('task') or\
        #                             core_instance.esh.extra.get('metadata',{}).get('tmp_status'))
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
        esh_driver = prepare_driver(request, identity_id)
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
        core_instance = convert_esh_instance(esh_driver, esh_instance,
                                           provider_id, identity_id, user)
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
        esh_driver = prepare_driver(request, identity_id)
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
        core_instance = convert_esh_instance(esh_driver, esh_instance,
                                           provider_id, identity_id, user)
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
        esh_driver = prepare_driver(request, identity_id)

        try:
            esh_instance = esh_driver.get_instance(instance_id)
            if not esh_instance:
                return instance_not_found(instance_id)
            task.destroy_instance_task(esh_driver, esh_instance)
            esh_instance = esh_driver.get_instance(instance_id)
            if esh_instance.extra\
               and 'task' not in esh_instance.extra:
                esh_instance.extra['task'] = 'queueing delete'
            core_instance = convert_esh_instance(esh_driver,
                                               esh_instance,
                                               provider_id,
                                               identity_id,
                                               user)
            if core_instance:
                core_instance.end_date_all()
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
