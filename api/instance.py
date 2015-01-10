from datetime import datetime
import time

from django.utils import timezone
from django.core.paginator import Paginator,\
    PageNotAnInteger, EmptyPage
from django.db.models import Q

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from rtwo.exceptions import ConnectionFailure
from libcloud.common.types import InvalidCredsError, MalformedResponseError

from threepio import logger

from core.models import AtmosphereUser as User
from core.models.identity import Identity
from core.models.instance import convert_esh_instance
from core.models.instance import Instance as CoreInstance
from core.models.provider import AccountProvider
from core.models.tag import Tag as CoreTag
from core.models.volume import convert_esh_volume

from service import task
from service.cache import get_cached_instances,\
    invalidate_cached_instances
from service.deploy import build_script
from service.driver import prepare_driver
from service.instance import redeploy_init, reboot_instance,\
    launch_instance, resize_instance, confirm_resize,\
    start_instance, resume_instance,\
    stop_instance, suspend_instance,\
    update_instance_metadata, _check_volume_attachment
from service.quota import check_over_quota
from service.exceptions import OverAllocationError, OverQuotaError,\
    SizeNotAvailable, HypervisorCapacityError, SecurityGroupNotCreated,\
    VolumeAttachConflict, VolumeMountConflict,\
        UnderThresholdError

from api import failure_response, invalid_creds,\
                connection_failure, malformed_response
from api.permissions import ApiAuthRequired
from api.serializers import InstanceStatusHistorySerializer
from api.serializers import InstanceSerializer, PaginatedInstanceSerializer
from api.serializers import InstanceHistorySerializer,\
    PaginatedInstanceHistorySerializer
from api.serializers import VolumeSerializer
from api.serializers import TagSerializer

def get_core_instance(request, provider_uuid, identity_uuid, instance_id):
    user = request.user
    esh_driver = prepare_driver(request, provider_uuid, identity_uuid)
    esh_instance = get_esh_instance(request, provider_uuid, identity_uuid, instance_id)
    core_instance = convert_esh_instance(esh_driver, esh_instance,
                                         provider_uuid, identity_uuid, user)
    return core_instance

def get_esh_instance(request, provider_uuid, identity_uuid, instance_id):
    esh_driver = prepare_driver(request, provider_uuid, identity_uuid)
    if not esh_driver:
        raise InvalidCredsError(
                "Provider_uuid && identity_uuid "
                "did not produce a valid combination")
    esh_instance = esh_driver.get_instance(instance_id)
    if not esh_instance:
        try:
            core_inst = CoreInstance.objects.get(
                provider_alias=instance_id,
                provider_machine__provider__uuid=provider_uuid,
                created_by_uuidentity__uuid=identity_uuid)
            core_inst.end_date_all()
        except CoreInstance.DoesNotExist:
            pass
        return esh_instance
    return esh_instance

class InstanceList(APIView):
    """
    Instances are the objects created when you launch a machine. They are
    represented by a unique ID, randomly generated on launch, important
    attributes of an Instance are:
    Name, Status (building, active, suspended), Size, Machine"""

    permission_classes = (ApiAuthRequired,)
    
    def get(self, request, provider_uuid, identity_uuid):
        """
        Returns a list of all instances
        """
        user = request.user
        esh_driver = prepare_driver(request, provider_uuid, identity_uuid)
        if not esh_driver:
            return invalid_creds(provider_uuid, identity_uuid)
        identity = Identity.objects.get(uuid=identity_uuid)
        try:
            esh_instance_list = get_cached_instances(identity=identity)
        except MalformedResponseError:
            return malformed_response(provider_uuid, identity_uuid)
        except InvalidCredsError:
            return invalid_creds(provider_uuid, identity_uuid)
        core_instance_list = [convert_esh_instance(esh_driver,
                                                   inst,
                                                   provider_uuid,
                                                   identity_uuid,
                                                   user)
                              for inst in esh_instance_list]
        #TODO: Core/Auth checks for shared instances
        serialized_data = InstanceSerializer(core_instance_list,
                                             context={"request":request},
                                             many=True).data
        response = Response(serialized_data)
        response['Cache-Control'] = 'no-cache'
        return response

    def post(self, request, provider_uuid, identity_uuid, format=None):
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
        #Check the data is valid
        missing_keys = valid_post_data(data)
        if missing_keys:
            return keys_not_found(missing_keys)

        #Pass these as args
        size_alias = data.pop('size_alias')
        machine_alias = data.pop('machine_alias')
        hypervisor_name = data.pop('hypervisor',None)
        try:
            logger.debug(data)
            core_instance = launch_instance(
                user, provider_uuid, identity_uuid,
                size_alias, machine_alias,
                ex_availability_zone=hypervisor_name,
                **data)
        except UnderThresholdError, ute:
            return under_threshold(ute)
        except OverQuotaError, oqe:
            return over_quota(oqe)
        except OverAllocationError, oae:
            return over_quota(oae)
        except SizeNotAvailable, snae:
            return size_not_availabe(snae)
        except SecurityGroupNotCreated:
            return connection_failure(provider_uuid, identity_uuid)
        except ConnectionFailure:
            return connection_failure(provider_uuid, identity_uuid)
        except InvalidCredsError:
            return invalid_creds(provider_uuid, identity_uuid)
        except Exception as exc:
            logger.exception("Encountered a generic exception. "
                             "Returning 409-CONFLICT")
            return failure_response(status.HTTP_409_CONFLICT,
                                    str(exc.message))

        serializer = InstanceSerializer(core_instance,
                                        context={"request":request},
                                        data=data)
        #NEVER WRONG
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)


def _sort_instance_history(history_instance_list, sort_by, descending=False):
    #Using the 'sort_by' variable, sort the list:
    if not sort_by or 'end_date' in sort_by:
        return sorted(history_instance_list, key=lambda ish:
                ish.end_date if ish.end_date else timezone.now(),
                reverse=descending)
    elif 'start_date' in sort_by:
        return sorted(history_instance_list, key=lambda ish:
                ish.start_date if ish.start_date else timezone.now(),
                reverse=descending)

def _filter_instance_history(history_instance_list, params):
    #Filter the list based on query strings
    for filter_key, value in params.items():
        if 'start_date' == filter_key:
            history_instance_list = history_instance_list.filter(
                start_date__gt=value)
        elif 'end_date' == filter_key:
            history_instance_list = history_instance_list.filter(
                Q(end_date=None) |
                Q(end_date__lt=value))
        elif 'ip_address' == filter_key:
            history_instance_list = history_instance_list.filter(
                ip_address__contains=value)
        elif 'alias' == filter_key:
            history_instance_list = history_instance_list.filter(
                provider_alias__contains=value)
    return history_instance_list


class InstanceHistory(APIView):
    """Paginated list of all instance history for specific user."""

    permission_classes = (ApiAuthRequired,)
    
    def get(self, request):
        """
        Authentication required, Retrieve a list of previously launched instances.
        """
        data = request.DATA
        params = request.QUERY_PARAMS.copy()
        emulate_name = params.pop('username', None)
        user = request.user
        # Support for staff users to emulate a specific user history
        if user.is_staff and emulate_name:
            emualate_name = emulate_name[0]  # Querystring conversion
            try:
                user = User.objects.get(username=emulate_name)
            except User.DoesNotExist:
                return failure_response(status.HTTP_401_UNAUTHORIZED,
                                        'Emulated User %s not found' %
                                        emualte_name)
        try:
            # List of all instances created by user
            sort_by = params.get('sort_by','')
            order_by = params.get('order_by','desc')
            history_instance_list = CoreInstance.objects.filter(
                created_by=user).order_by("-start_date")
            history_instance_list = _filter_instance_history(
                    history_instance_list, params)
            history_instance_list = _sort_instance_history(
                    history_instance_list, sort_by, 'desc' in order_by.lower())
        except Exception as e:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                'Bad query string caused filter validation errors : %s'
                % (e,))

        page = params.get('page')
        if page or len(history_instance_list) == 0:
            paginator = Paginator(history_instance_list, 20,
                                  allow_empty_first_page=True)
        else:
            paginator = Paginator(history_instance_list,
                                  len(history_instance_list),
                                  allow_empty_first_page=True)
        try:
            history_instance_page = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            history_instance_page = paginator.page(1)
        except EmptyPage:
            # Page is out of range.
            # deliver last page of results.
            history_instance_page = paginator.page(paginator.num_pages)
        serialized_data = PaginatedInstanceHistorySerializer(
                history_instance_page, context={'request':request}).data
        response = Response(serialized_data)
        response['Cache-Control'] = 'no-cache'
        return response

class InstanceHistoryDetail(APIView):
    """instance history for specific instance."""

    permission_classes = (ApiAuthRequired,)
    
    def get(self, request, instance_id):
        """
        Authentication required, Retrieve a list of previously launched instances.
        """
        data = request.DATA
        params = request.QUERY_PARAMS.copy()
        user = User.objects.filter(username=request.user)
        if user and len(user) > 0:
            user = user[0]
        else:
            return failure_response(status.HTTP_401_UNAUTHORIZED,
                                    'Request User %s not found' %
                                    user)
        emulate_name = params.pop('username', None)
        # Support for staff users to emulate a specific user history
        if user.is_staff and emulate_name:
            emualate_name = emulate_name[0]  # Querystring conversion
            user = User.objects.filter(username=emulate_name)
            if user and len(user) > 0:
                user = user[0]
            else:
                return failure_response(status.HTTP_401_UNAUTHORIZED,
                                        'Emulated User %s not found' %
                                        emualte_name)
        # List of all instances matching user, instance_id
        core_instance = CoreInstance.objects.filter(
            created_by=user, provider_alias=instance_id).order_by("-start_date")
        if core_instance and len(core_instance) > 0:
            core_instance = core_instance[0]
        else:
            return failure_response(status.HTTP_401_UNAUTHORIZED,
                                    'Instance %s not found' %
                                    instance_id)
        serialized_data = InstanceHistorySerializer(core_instance).data
        response = Response(serialized_data)
        response['Cache-Control'] = 'no-cache'
        return response

class InstanceStatusHistoryDetail(APIView):
    """List of instance status history for specific instance."""

    permission_classes = (ApiAuthRequired,)
    
    def get(self, request, instance_id):
        """
        Authentication required, Retrieve a list of previously launched instances.
        """
        data = request.DATA
        params = request.QUERY_PARAMS.copy()
        user = User.objects.filter(username=request.user)
        if user and len(user) > 0:
            user = user[0]
        else:
            return failure_response(status.HTTP_401_UNAUTHORIZED,
                                    'Request User %s not found' %
                                    user)
        emulate_name = params.pop('username', None)
        # Support for staff users to emulate a specific user history
        if user.is_staff and emulate_name:
            emualate_name = emulate_name[0]  # Querystring conversion
            user = User.objects.filter(username=emulate_name)
            if user and len(user) > 0:
                user = user[0]
            else:
                return failure_response(status.HTTP_401_UNAUTHORIZED,
                                        'Emulated User %s not found' %
                                        emualte_name)
        # List of all instances matching user, instance_id
        core_instance = CoreInstance.objects.filter(
            created_by=user,
            provider_alias=instance_id).order_by("-start_date")
        if core_instance and len(core_instance) > 0:
            core_instance = core_instance[0]
        else:
            return failure_response(status.HTTP_401_UNAUTHORIZED,
                                    'Instance %s not found' %
                                    instance_id)
        status_history = core_instance\
                .instancestatushistory_set.order_by('start_date')
        serialized_data = InstanceStatusHistorySerializer(
                status_history, many=True).data
        response = Response(serialized_data)
        response['Cache-Control'] = 'no-cache'
        return response

class InstanceAction(APIView):
    """
    This endpoint will allow you to run a specific action on an instance.
    The GET method will retrieve all available actions and any parameters that are required.
    The POST method expects DATA: {"action":...}
                            Returns: 200, data: {'result':'success',...}
                                     On Error, a more specfific message applies.
    Data variables:
     ___
    * action - The action you wish to take on your instance
    * action_params - any parameters required (as detailed on the api) to run the requested action.

    Instances are the objects created when you launch a machine. They are
    represented by a unique ID, randomly generated on launch, important
    attributes of an Instance are:
    Name, Status (building, active, suspended), Size, Machine"""

    permission_classes = (ApiAuthRequired,)
    
    def get(self, request, provider_uuid, identity_uuid, instance_id):
        """Authentication Required, List all available instance actions ,including necessary parameters.
        """
        actions = [{"action":"attach_volume",
                 "action_params":{
                     "volume_id":"required",
                     "device":"optional",
                     "mount_location":"optional"},
                 "description":"Attaches the volume <id> to instance"},
                {"action":"mount_volume",
                 "action_params":{
                     "volume_id":"required",
                     "device":"optional",
                     "mount_location":"optional"
                     },
                 "description":"Unmount the volume <id> from instance"},
                {"action":"unmount_volume",
                 "action_params":{
                     "volume_id":"required",
                     },
                 "description":"Mount the volume <id> to instance"},
                {"action":"detach_volume",
                 "action_params":{"volume_id":"required"},
                 "description":"Detaches the volume <id> to instance"},
                {"action":"resize",
                 "action_params":{"size":"required"},
                 "description":"Resize instance to size <id>"},
                {"action":"confirm_resize",
                 "description":"Confirm the instance works after resize."},
                {"action":"revert_resize",
                 "description":"Revert the instance if resize fails."},
                {"action":"suspend",
                 "description":"Suspend the instance."},
                {"action":"resume",
                 "description":"Resume the instance."},
                {"action":"start",
                 "description":"Start the instance."},
                {"action":"stop",
                 "description":"Stop the instance."},
                {"action":"reboot",
                 "action_params":{"reboot_type (optional)":"SOFT/HARD"},
                 "description":"Stop the instance."},
                {"action":"console",
                 "description":"Get noVNC Console."}]
        response = Response(actions, status=status.HTTP_200_OK)
        return response

    def post(self, request, provider_uuid, identity_uuid, instance_id):
        """Authentication Required, Attempt a specific instance action, including necessary parameters.
        """
        #Service-specific call to action
        action_params = request.DATA
        if not action_params.get('action', None):
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                'POST request to /action require a BODY with \'action\'.')
        result_obj = None
        user = request.user
        esh_driver = prepare_driver(request, provider_uuid, identity_uuid)
        if not esh_driver:
            return invalid_creds(provider_uuid, identity_uuid)

        esh_instance = esh_driver.get_instance(instance_id)
        if not esh_instance:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                'Instance %s no longer exists' % (instance_id,))
        action = action_params['action']
        try:
            if 'volume' in action:
                volume_id = action_params.get('volume_id')
                mount_location = action_params.get('mount_location', None)
                device = action_params.get('device', None)
                if 'attach_volume' == action:
                    if mount_location == 'null' or mount_location == 'None':
                        mount_location = None
                    if device == 'null' or device == 'None':
                        device = None
                    future_mount_location = task.attach_volume_task(esh_driver, esh_instance.alias,
                                            volume_id, device, mount_location)
                elif 'mount_volume' == action:
                    future_mount_location = task.mount_volume_task(esh_driver, esh_instance.alias,
                            volume_id, device, mount_location)
                elif 'unmount_volume' == action:
                    (result, error_msg) = task.unmount_volume_task(esh_driver, esh_instance.alias,
                            volume_id, device, mount_location)
                elif 'detach_volume' == action:
                    (result, error_msg) = task.detach_volume_task(
                        esh_driver,
                        esh_instance.alias,
                        volume_id)
                    if not result and error_msg:
                        #Return reason for failed detachment
                        return failure_response(
                            status.HTTP_400_BAD_REQUEST,
                            error_msg)
                #Task complete, convert the volume and return the object
                esh_volume = esh_driver.get_volume(volume_id)
                core_volume = convert_esh_volume(esh_volume,
                                                 provider_uuid,
                                                 identity_uuid,
                                                 user)
                result_obj = VolumeSerializer(core_volume,
                                              context={"request":request}
                                              ).data
            elif 'resize' == action:
                size_alias = action_params.get('size', '')
                if type(size_alias) == int:
                    size_alias = str(size_alias)
                resize_instance(esh_driver, esh_instance, size_alias,
                               provider_uuid, identity_uuid, user)
            elif 'confirm_resize' == action:
                confirm_resize(esh_driver, esh_instance,
                               provider_uuid, identity_uuid, user)
            elif 'revert_resize' == action:
                esh_driver.revert_resize_instance(esh_instance)
            elif 'redeploy' == action:
                redeploy_init(esh_driver, esh_instance, countdown=None)
            elif 'resume' == action:
                resume_instance(esh_driver, esh_instance,
                                provider_uuid, identity_uuid, user)
            elif 'suspend' == action:
                suspend_instance(esh_driver, esh_instance,
                                 provider_uuid, identity_uuid, user)
            elif 'start' == action:
                start_instance(esh_driver, esh_instance,
                               provider_uuid, identity_uuid, user)
            elif 'stop' == action:
                stop_instance(esh_driver, esh_instance,
                              provider_uuid, identity_uuid, user)
            elif 'reset_network' == action:
                esh_driver.reset_network(esh_instance)
            elif 'console' == action:
                result_obj = esh_driver._connection.ex_vnc_console(esh_instance)
            elif 'reboot' == action:
                reboot_type = action_params.get('reboot_type', 'SOFT')
                reboot_instance(esh_driver, esh_instance,
                        identity_uuid, user, reboot_type)
            elif 'rebuild' == action:
                machine_alias = action_params.get('machine_alias', '')
                machine = esh_driver.get_machine(machine_alias)
                esh_driver.rebuild_instance(esh_instance, machine)
            else:
                return failure_response(
                    status.HTTP_400_BAD_REQUEST,
                    'Unable to to perform action %s.' % (action))
            #ASSERT: The action was executed successfully
            api_response = {
                'result': 'success',
                'message': 'The requested action <%s> was run successfully'
                % action_params['action'],
                'object': result_obj,
            }
            response = Response(api_response, status=status.HTTP_200_OK)
            return response
        ### Exception handling below..
        except HypervisorCapacityError, hce:
            return over_capacity(hce)
        except OverQuotaError, oqe:
            return over_quota(oqe)
        except OverAllocationError, oae:
            return over_quota(oae)
        except SizeNotAvailable, snae:
            return size_not_availabe(snae)
        except ConnectionFailure:
            return connection_failure(provider_uuid, identity_uuid)
        except InvalidCredsError:
            return invalid_creds(provider_uuid, identity_uuid)
        except VolumeMountConflict, vmc:
            return mount_failed(vmc)
        except NotImplemented, ne:
            return failure_response(
                status.HTTP_404_NOT_FOUND,
                "The requested action %s is not available on this provider"
                % action_params['action'])
        except Exception, exc:
            logger.exception("Exception occurred processing InstanceAction")
            message = exc.message
            if message.startswith('409 Conflict'):
                return failure_response(
                    status.HTTP_409_CONFLICT,
                    message)
            return failure_response(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "The requested action %s encountered "
                "an irrecoverable exception: %s"
                % (action_params['action'], message))


class Instance(APIView):
    """
    Instances are the objects created when you launch a machine. They are
    represented by a unique ID, randomly generated on launch, important
    attributes of an Instance are:
    Name, Status (building, active, suspended), Size, Machine"""
    #renderer_classes = (JSONRenderer, JSONPRenderer)

    permission_classes = (ApiAuthRequired,)
    
    def get(self, request, provider_uuid, identity_uuid, instance_id):
        """
        Authentication Required, get instance details.
        """
        user = request.user
        esh_driver = prepare_driver(request, provider_uuid, identity_uuid)
        if not esh_driver:
            return invalid_creds(provider_uuid, identity_uuid)
        esh_instance = esh_driver.get_instance(instance_id)
        if not esh_instance:
            try:
                core_inst = CoreInstance.objects.get(
                    provider_alias=instance_id,
                    provider_machine__provider__uuid=provider_uuid,
                    created_by_uuidentity__uuid=identity_uuid)
                core_inst.end_date_all()
            except CoreInstance.DoesNotExist:
                pass
            return instance_not_found(instance_id)
        core_instance = convert_esh_instance(esh_driver, esh_instance,
                                             provider_uuid, identity_uuid, user)
        serialized_data = InstanceSerializer(core_instance,
                                             context={"request":request}).data
        response = Response(serialized_data)
        response['Cache-Control'] = 'no-cache'
        return response

    def patch(self, request, provider_uuid, identity_uuid, instance_id):
        """Authentication Required, update metadata about the instance"""
        user = request.user
        data = request.DATA
        esh_driver = prepare_driver(request, provider_uuid, identity_uuid)
        if not esh_driver:
            return invalid_creds(provider_uuid, identity_uuid)
        esh_instance = esh_driver.get_instance(instance_id)
        if not esh_instance:
            return instance_not_found(instance_id)
        #Gather the DB related item and update
        core_instance = convert_esh_instance(esh_driver, esh_instance,
                                             provider_uuid, identity_uuid, user)
        serializer = InstanceSerializer(core_instance, data=data,
                                        context={"request":request}, partial=True)
        if serializer.is_valid():
            logger.info('metadata = %s' % data)
            update_instance_metadata(esh_driver, esh_instance, data,
                    replace=False)
            serializer.save()
            invalidate_cached_instances(identity=Identity.objects.get(uuid=identity_uuid))
            response = Response(serializer.data)
            logger.info('data = %s' % serializer.data)
            response['Cache-Control'] = 'no-cache'
            return response
        else:
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, provider_uuid, identity_uuid, instance_id):
        """Authentication Required, update metadata about the instance"""
        user = request.user
        data = request.DATA
        #Ensure item exists on the server first
        esh_driver = prepare_driver(request, provider_uuid, identity_uuid)
        if not esh_driver:
            return invalid_creds(provider_uuid, identity_uuid)
        esh_instance = esh_driver.get_instance(instance_id)
        if not esh_instance:
            return instance_not_found(instance_id)
        #Gather the DB related item and update
        core_instance = convert_esh_instance(esh_driver, esh_instance,
                                             provider_uuid, identity_uuid, user)
        serializer = InstanceSerializer(core_instance, data=data,
                                        context={"request":request})
        if serializer.is_valid():
            logger.info('metadata = %s' % data)
            update_instance_metadata(esh_driver, esh_instance, data)
            serializer.save()
            invalidate_cached_instances(identity=Identity.objects.get(uuid=identity_uuid))
            response = Response(serializer.data)
            logger.info('data = %s' % serializer.data)
            response['Cache-Control'] = 'no-cache'
            return response
        else:
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, provider_uuid, identity_uuid, instance_id):
        """Authentication Required, TERMINATE the instance.

        Be careful, there is no going back once you've deleted an instance.
        """
        user = request.user
        esh_driver = prepare_driver(request, provider_uuid, identity_uuid)
        if not esh_driver:
            return invalid_creds(provider_uuid, identity_uuid)
        try:
            esh_instance = esh_driver.get_instance(instance_id)
            if not esh_instance:
                return instance_not_found(instance_id)
            #Test that there is not an attached volume BEFORE we destroy
            _check_volume_attachment(esh_driver, esh_instance)
            task.destroy_instance_task(esh_instance, identity_uuid)
            invalidate_cached_instances(identity=Identity.objects.get(uuid=identity_uuid))
            existing_instance = esh_driver.get_instance(instance_id)
            if existing_instance:
                #Instance will be deleted soon...
                esh_instance = existing_instance
                if esh_instance.extra\
                   and 'task' not in esh_instance.extra:
                    esh_instance.extra['task'] = 'queueing delete'
            core_instance = convert_esh_instance(esh_driver, esh_instance,
                                                 provider_uuid, identity_uuid,
                                                 user)
            if core_instance:
                core_instance.end_date_all()
            else:
                logger.warn("Unable to find core instance %s." % (instance_id))
            serialized_data = InstanceSerializer(core_instance,
                                                 context={"request":request}).data
            response = Response(serialized_data, status=status.HTTP_200_OK)
            response['Cache-Control'] = 'no-cache'
            return response
        except (Identity.DoesNotExist) as exc:
            return failure_response(status.HTTP_400_BAD_REQUEST,
                                    "Invalid provider_uuid or identity_uuid.")
        except VolumeAttachConflict as exc:
            message = exc.message
            return failure_response(status.HTTP_409_CONFLICT, message)
        except ConnectionFailure:
            return connection_failure(provider_uuid, identity_uuid)
        except InvalidCredsError:
            return invalid_creds(provider_uuid, identity_uuid)



class InstanceTagList(APIView):
    """
        Tags are a easy way to allow users to group several images as similar
        based on a feature/program of the application.
    """
    permission_classes = (ApiAuthRequired,)
    
    def get(self, request, provider_uuid, identity_uuid, instance_id, *args, **kwargs):
        """
        List all public tags.
        """
        core_instance = get_core_instance(request, provider_uuid,
                                          identity_uuid, instance_id)
        if not core_instance:
            instance_not_found(instance_id)
        tags = core_instance.tags.all()
        serializer = TagSerializer(tags, many=True)
        return Response(serializer.data)

    def post(self, request, provider_uuid, identity_uuid, instance_id,
             *args, **kwargs):
        """Create a new tag resource
        Params:name -- Name of the new Tag
        Returns: 
        Status Code: 201 Body: A new Tag object
        Status Code: 400 Body: Errors (Duplicate/Invalid Name)
        """
        user = request.user
        data = request.DATA.copy()
        if 'name' not in data:
            return Response("Missing 'name' in POST data",
                    status=status.HTTP_400_BAD_REQUEST)

        core_instance = get_core_instance(request, provider_uuid, identity_uuid, instance_id)
        if not core_instance:
            instance_not_found(instance_id)

        created = False
        same_name_tags = CoreTag.objects.filter(name__iexact=data['name'])
        if same_name_tags:
            add_tag = same_name_tags[0]
        else:
            data['user'] = user.username
            data['name'] = data['name'].lower()
            #description is optional
            serializer = TagSerializer(data=data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            serializer.save()
            add_tag = serializer.object
            created = True
        core_instance.tags.add(add_tag)
        return Response(status=status.HTTP_204_NO_CONTENT)


class InstanceTagDetail(APIView):
    """
        Tags are a easy way to allow users to group several images as similar
        based on a feature/program of the application.

        This API resource allows you to Retrieve, Update, or Delete your Tag.
    """
    permission_classes = (ApiAuthRequired,)
    
    def delete(self, request, provider_uuid, identity_uuid, instance_id,  tag_slug, *args, **kwargs):
        """
        Remove the tag, if it is no longer in use.
        """
        core_instance = get_core_instance(request, provider_uuid, identity_uuid, instance_id)
        if not core_instance:
            instance_not_found(instance_id)
        try:
            tag = core_instance.tags.get(name__iexact=tag_slug)
        except CoreTag.DoesNotExist:
            return failure_response(status.HTTP_404_NOT_FOUND, 
                                    'Tag %s not found on instance' % tag_slug)
        core_instance.tags.remove(tag)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get(self, request, provider_uuid, identity_uuid, instance_id,  tag_slug, *args, **kwargs):
        """
        Return the credential information for this tag
        """
        core_instance = get_core_instance(request, provider_uuid, identity_uuid, instance_id)
        if not core_instance:
            instance_not_found(instance_id)
        try:
            tag = core_instance.tags.get(name__iexact=tag_slug)
        except CoreTag.DoesNotExist:
            return Response(['Tag does not exist'],
                            status=status.HTTP_404_NOT_FOUND)
        serializer = TagSerializer(tag)
        return Response(serializer.data)


def valid_post_data(data):
    """
    Return any missing required post key names.
    """
    required = ['machine_alias', 'size_alias', 'name']
    #Return any keys that don't match criteria
    return [key for key in required
            #Key must exist and have a non-empty value.
            if key not in data
            or (type(data[key]) == str and len(data[key]) > 0)]


def keys_not_found(missing_keys):
    return failure_response(
        status.HTTP_400_BAD_REQUEST,
        'Missing data for variable(s): %s' % missing_keys)


def instance_not_found(instance_id):
    return failure_response(
        status.HTTP_404_NOT_FOUND,
        'Instance %s does not exist' % instance_id)


def size_not_availabe(sna_exception):
    return failure_response(
        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        sna_exception.message)


def over_capacity(capacity_exception):
    return failure_response(
        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        capacity_exception.message)


def under_threshold(threshold_exception):
    return failure_response(
        status.HTTP_400_BAD_REQUEST,
        threshold_exception.message)


def over_quota(quota_exception):
    return failure_response(
        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        quota_exception.message)


def mount_failed(exception):
    return failure_response(
        status.HTTP_409_CONFLICT,
        exception.message)

def over_allocation(allocation_exception):
    return failure_response(
        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        allocation_exception.message)
