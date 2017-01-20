from django.utils import timezone
from django.db.models import Q

from rest_framework import status
from rest_framework.response import Response

from threepio import logger
from atmosphere import settings

from core.exceptions import ProviderNotActive
from core.models import AtmosphereUser as User
from core.models.allocation_source import AllocationSource
from core.models.identity import Identity
from core.models.instance import convert_esh_instance
from core.models.instance import Instance as CoreInstance
from core.models.boot_script import _save_scripts_to_instance
from core.models.tag import Tag as CoreTag
from core.models.provider import Provider

from service import task
from service.cache import get_cached_instances,\
    invalidate_cached_instances
from service.driver import prepare_driver
from service.exceptions import (
    OverAllocationError, OverQuotaError,
    SizeNotAvailable, HypervisorCapacityError, SecurityGroupNotCreated,
    VolumeAttachConflict, VolumeMountConflict, InstanceDoesNotExist,
    UnderThresholdError, ActionNotAllowed, Unauthorized,
    # Technically owned by another
    socket_error, ConnectionFailure, LibcloudInvalidCredsError, LibcloudBadResponseError
    )
from service.instance import (
    run_instance_action,
    launch_instance)
from service.tasks.driver import update_metadata

from api import failure_response, invalid_creds,\
    connection_failure, malformed_response
from api.decorators import emulate_user
from api.exceptions import (
    inactive_provider, size_not_available, mount_failed, over_quota,
    under_threshold, over_capacity, instance_not_found)
from api.pagination import OptionalPagination
from api.v1.serializers import InstanceStatusHistorySerializer,\
    InstanceSerializer, InstanceHistorySerializer, VolumeSerializer,\
    TagSerializer
from api.v1.views.base import AuthAPIView, AuthListAPIView


def get_core_instance(request, provider_uuid, identity_uuid, instance_id):
    user = request.user
    esh_driver = prepare_driver(request, provider_uuid, identity_uuid)
    esh_instance = get_esh_instance(request, provider_uuid, identity_uuid,
                                    instance_id)
    core_instance = convert_esh_instance(esh_driver, esh_instance,
                                         provider_uuid, identity_uuid, user)
    return core_instance


def get_esh_instance(request, provider_uuid, identity_uuid, instance_id):
    esh_driver = prepare_driver(request, provider_uuid, identity_uuid)
    if not esh_driver:
        raise LibcloudInvalidCredsError(
            "Provider_uuid && identity_uuid "
            "did not produce a valid combination")
    esh_instance = None
    try:
        esh_instance = esh_driver.get_instance(instance_id)
    except (socket_error, ConnectionFailure):
        return connection_failure(provider_uuid, identity_uuid)
    except LibcloudInvalidCredsError:
        return invalid_creds(provider_uuid, identity_uuid)
    except Exception as exc:
        logger.exception("Encountered a generic exception. "
                         "Returning 409-CONFLICT")
        return failure_response(status.HTTP_409_CONFLICT,
                                str(exc.message))

    if not esh_instance:
        # End date everything
        try:
            core_inst = CoreInstance.objects.get(
                provider_alias=instance_id,
                source__provider__uuid=provider_uuid,
                created_by_identity__uuid=identity_uuid)
            core_inst.end_date_all()
        except CoreInstance.DoesNotExist:
            pass
    return esh_instance


class InstanceList(AuthAPIView):

    """
    Instances are the objects created when you launch a machine. They are
    represented by a unique ID, randomly generated on launch, important
    attributes of an Instance are:
    Name, Status (building, active, suspended), Size, Machine"""

    def get(self, request, provider_uuid, identity_uuid):
        """
        Returns a list of all instances
        """
        user = request.user
        try:
            esh_driver = prepare_driver(request, provider_uuid, identity_uuid)
        except ProviderNotActive as pna:
            return inactive_provider(pna)
        except Exception as e:
            return failure_response(
                status.HTTP_409_CONFLICT,
                e.message)
        if not esh_driver:
            return invalid_creds(provider_uuid, identity_uuid)
        identity = Identity.objects.get(uuid=identity_uuid)
        # Probably redundant
        if not user.can_use_identity(identity.id):
            return invalid_creds(provider_uuid, identity_uuid)
        try:
            esh_instance_list = get_cached_instances(identity=identity)
        except LibcloudBadResponseError:
            return malformed_response(provider_uuid, identity_uuid)
        except (socket_error, ConnectionFailure):
            return connection_failure(provider_uuid, identity_uuid)
        except LibcloudInvalidCredsError:
            return invalid_creds(provider_uuid, identity_uuid)
        core_instance_list = [convert_esh_instance(esh_driver,
                                                   inst,
                                                   provider_uuid,
                                                   identity_uuid,
                                                   user)
                              for inst in esh_instance_list]
        # TODO: Core/Auth checks for shared instances
        serialized_data = InstanceSerializer(core_instance_list,
                                             context={"request": request},
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
        data = request.data
        user = request.user
        # Check the data is valid
        missing_keys = valid_post_data(data)
        if missing_keys:
            return keys_not_found(missing_keys)
        # Pass these as args
        size_alias = data.pop("size_alias")
        allocation_source_id = data.pop("allocation_source_id",None)
        machine_alias = data.pop("machine_alias")
        hypervisor_name = data.pop("hypervisor", None)
        if hypervisor_name:
            # Previous method passed this with 'None' but that fails now.
            # This check will only add the ex_ value if it is 'truthy'.
            data['ex_hypervisor_name'] = hypervisor_name
        deploy = data.pop("deploy", True)
        if type(deploy) in [str, unicode] and deploy.lower() == "false":
            deploy = False
        elif not isinstance(deploy, bool):
            deploy = True
        boot_scripts = data.pop("scripts", [])
        try:
            logger.debug(data)
            if not settings.USE_ALLOCATION_SOURCE:
                allocation_source = None
            else:
                allocation_source = AllocationSource.objects.get(
                    source_id=allocation_source_id)
            core_instance = launch_instance(
                user, identity_uuid,
                size_alias, machine_alias,
                deploy=deploy, **data)
        except UnderThresholdError as ute:
            return under_threshold(ute)
        except OverQuotaError as oqe:
            return over_quota(oqe)
        except OverAllocationError as oae:
            return over_quota(oae)
        except Unauthorized as auth_invalid:
            return invalid_creds(provider_uuid, identity_uuid)
        except SizeNotAvailable as snae:
            return size_not_available(snae)
        except SecurityGroupNotCreated:
            return connection_failure(provider_uuid, identity_uuid)
        except (socket_error, ConnectionFailure):
            return connection_failure(provider_uuid, identity_uuid)
        except LibcloudInvalidCredsError:
            return invalid_creds(provider_uuid, identity_uuid)
        except Exception as exc:
            logger.exception("Encountered a generic exception. "
                             "Returning 409-CONFLICT")
            return failure_response(status.HTTP_409_CONFLICT,
                                    str(exc.message))

        serializer = InstanceSerializer(core_instance,
                                        context={"request": request},
                                        data=data)
        if serializer.is_valid():
            instance = serializer.save()
            if boot_scripts:
                _save_scripts_to_instance(instance, boot_scripts)
            instance.change_allocation_source(allocation_source)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)


def _sort_instance_history(history_instance_list, sort_by, descending=False):
    # Using the 'sort_by' variable, sort the list:
    if not sort_by or 'end_date' in sort_by:
        return sorted(history_instance_list, key=lambda ish:
                      ish.end_date if ish.end_date else timezone.now(),
                      reverse=descending)
    elif 'start_date' in sort_by:
        return sorted(history_instance_list, key=lambda ish:
                      ish.start_date if ish.start_date else timezone.now(),
                      reverse=descending)


def _filter_instance_history(history_instance_list, params):
    # Filter the list based on query strings
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


class InstanceHistory(AuthListAPIView):

    """Instance history for a specific user."""
    pagination_class = OptionalPagination

    serializer_class = InstanceHistorySerializer

    @emulate_user
    def get_queryset(self):
        """
        Authentication required, Retrieve a list of previously launched
        instances.
        """
        # List of all instances created by user
        sort_by = self.request.query_params.get('sort_by', '')
        order_by = self.request.query_params.get('order_by', 'desc')
        history_instance_list = CoreInstance.objects.filter(
            created_by=self.request.user).order_by("-start_date")
        history_instance_list = _filter_instance_history(
            history_instance_list, self.request.query_params)
        history_instance_list = _sort_instance_history(
            history_instance_list, sort_by, 'desc' in order_by.lower())
        return history_instance_list


class InstanceHistoryDetail(AuthAPIView):

    """
    Instance history for specific instance.
    """

    def get(self, request, instance_id):
        """
        Authentication required, Retrieve a list of previously launched
        instances.
        """
        params = request.query_params.copy()
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
            emulate_name = emulate_name[0]  # Querystring conversion
            user = User.objects.filter(username=emulate_name)
            if user and len(user) > 0:
                user = user[0]
            else:
                return failure_response(status.HTTP_401_UNAUTHORIZED,
                                        'Emulated User %s not found' %
                                        emulate_name)
        # List of all instances matching user, instance_id
        core_instance =\
            CoreInstance.objects.filter(
                created_by=user,
                provider_alias=instance_id).order_by("-start_date")
        if core_instance and len(core_instance) > 0:
            core_instance = core_instance[0]
        else:
            return failure_response(status.HTTP_401_UNAUTHORIZED,
                                    'Instance %s not found' %
                                    instance_id)
        serialized_data = InstanceHistorySerializer(
            core_instance,
            context={"request": request},
            many=True).data
        response = Response(serialized_data)
        response['Cache-Control'] = 'no-cache'
        return response


class InstanceStatusHistoryDetail(AuthAPIView):

    """
    List of instance status history for specific instance.
    """

    def get(self, request, instance_id):
        """
        Authentication required, Retrieve a list of previously launched
        instances.
        """
        params = request.query_params.copy()
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
            emulate_name = emulate_name[0]  # Querystring conversion
            user = User.objects.filter(username=emulate_name)
            if user and len(user) > 0:
                user = user[0]
            else:
                return failure_response(status.HTTP_401_UNAUTHORIZED,
                                        'Emulated User %s not found' %
                                        emulate_name)
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




def _further_process_result(request, action, result):
    """
    Provide additional serialization if the `action` has a
    `result` requiring processing.
    """
    if 'volume' in action:
        return VolumeSerializer(result,
                                context={"request": request}).data
    else:
        return result


class InstanceAction(AuthAPIView):

    """
    This endpoint will allow you to run a specific action on an instance.
    The GET method will retrieve all available actions and any parameters
    that are required.
    The POST method expects DATA: {"action":...}
        Returns: 200, data: {'result':'success',...}
        On Error, a more specfific message applies.
    Data variables:
     ___
    * action - The action you wish to take on your instance
    * action_params - any parameters required (as detailed on the api) to
      run the requested action.

    Instances are the objects created when you launch a machine. They are
    represented by a unique ID, randomly generated on launch, important
    attributes of an Instance are:
    Name, Status (building, active, suspended), Size, Machine
    """

    def get(self, request, provider_uuid, identity_uuid, instance_id):
        """Authentication Required, List all available instance actions,
        including necessary parameters.
        """
        actions = [
            {"action": "attach_volume",
             "action_params": {
                 "volume_id": "required",
                 "device": "optional",
                 "mount_location": "optional"},
             "description": "Attaches the volume <id> to instance"},
            {"action": "mount_volume",
             "action_params": {
                 "volume_id": "required",
                 "device": "optional",
                 "mount_location": "optional"},
             "description": "Unmount the volume <id> from instance"},
            {"action": "unmount_volume",
             "action_params": {"volume_id": "required"},
             "description": "Mount the volume <id> to instance"},
            {"action": "detach_volume",
             "action_params": {"volume_id": "required"},
             "description": "Detaches the volume <id> to instance"},
            {"action": "resize",
             "action_params": {"size": "required"},
             "description": "Resize instance to size <id>"},
            {"action": "confirm_resize",
             "description": "Confirm the instance works after resize."},
            {"action": "revert_resize",
             "description": "Revert the instance if resize fails."},
            {"action": "suspend",
             "description": "Suspend the instance."},
            {"action": "resume",
             "description": "Resume the instance."},
            {"action": "start",
             "description": "Start the instance."},
            {"action": "stop",
             "description": "Stop the instance."},
            {"action": "reboot",
             "action_params": {"reboot_type (optional)": "SOFT/HARD"},
             "description": "Stop the instance."},
            {"action": "console",
             "description": "Get noVNC Console."}]
        response = Response(actions, status=status.HTTP_200_OK)
        return response

    def post(self, request, provider_uuid, identity_uuid, instance_id):
        """Authentication Required, Attempt a specific instance action,
        including necessary parameters.
        """
        # Service-specific call to action
        action_params = request.data
        if not action_params.get('action', None):
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                'POST request to /action require a BODY with \'action\'.')
        result_obj = None
        user = request.user
        identity = Identity.objects.get(uuid=identity_uuid)
        action = action_params['action']
        try:
            result_obj = run_instance_action(user, identity, instance_id, action, action_params)
            result_obj = _further_process_result(request, action, result_obj)
            api_response = {
                'result': 'success',
                'message': 'The requested action <%s> was run successfully' % (action_params['action'],),
                'object': result_obj,
            }
            response = Response(api_response, status=status.HTTP_200_OK)
            return response
        except (socket_error, ConnectionFailure):
            return connection_failure(provider_uuid, identity_uuid)
        except ProviderNotActive as pna:
            return inactive_provider(pna)
        except InstanceDoesNotExist as dne:
            return failure_response(
                status.HTTP_404_NOT_FOUND,
                'Instance %s no longer exists' % (dne.message,))
        except LibcloudInvalidCredsError:
            return invalid_creds(provider_uuid, identity_uuid)
        except HypervisorCapacityError as hce:
            return over_capacity(hce)
        except OverQuotaError as oqe:
            return over_quota(oqe)
        except OverAllocationError as oae:
            return over_quota(oae)
        except SizeNotAvailable as snae:
            return size_not_available(snae)
        except (socket_error, ConnectionFailure):
            return connection_failure(provider_uuid, identity_uuid)
        except LibcloudInvalidCredsError:
            return invalid_creds(provider_uuid, identity_uuid)
        except VolumeMountConflict as vmc:
            return mount_failed(vmc)
        except NotImplemented:
            return failure_response(
                status.HTTP_409_CONFLICT,
                "The requested action %s is not available on this provider."
                % action_params['action'])
        except ActionNotAllowed:
            return failure_response(
                status.HTTP_409_CONFLICT,
                "The requested action %s has been explicitly "
                "disabled on this provider." % action_params['action'])
        except Exception as exc:
            logger.exception("Exception occurred processing InstanceAction")
            message = exc.message
            if message.startswith('409 Conflict'):
                return failure_response(
                    status.HTTP_409_CONFLICT,
                    message)
            return failure_response(
                status.HTTP_403_FORBIDDEN,
                "The requested action %s encountered "
                "an irrecoverable exception: %s"
                % (action_params['action'], message))


class Instance(AuthAPIView):

    """
    Instances are the objects created when you launch a machine. They are
    represented by a unique ID, randomly generated on launch, important
    attributes of an Instance are:
        Name, Status (building, active, suspended), Size, Machine
    """

    def get(self, request, provider_uuid, identity_uuid, instance_id):
        """
        Authentication Required, get instance details.
        """
        user = request.user
        # NOTE: This 'Scheme' should be used across
        #       the ENTIRE API v1 (Machines, Volumes, Sizes)
        # NOTE: Especially the part below, where you end date
        #       all the things that are 'inactive'
        try:
            provider = Provider.objects.get(uuid=provider_uuid)
            if not provider.is_active():
                raise ProviderNotActive(provider)
        except Provider.DoesNotExist:
            return invalid_creds(provider_uuid, identity_uuid)
        except ProviderNotActive as pna:
            return inactive_provider(pna)

        # Cleared provider testing -- ready for driver prep.
        try:
            esh_driver = prepare_driver(request, provider_uuid, identity_uuid)
            logger.info("Looking for %s" % instance_id)
            esh_instance = esh_driver.get_instance(instance_id)
        except (socket_error, ConnectionFailure):
            return connection_failure(provider_uuid, identity_uuid)
        except LibcloudInvalidCredsError:
            return invalid_creds(provider_uuid, identity_uuid)
        except Exception as exc:
            logger.exception("Encountered a generic exception. "
                             "Returning 409-CONFLICT")
            return failure_response(status.HTTP_409_CONFLICT,
                                    str(exc.message))

        # NOTE: Especially THIS part below, where you end date all the
        #       things that are 'inactive'
        if not esh_instance:
            try:
                core_inst = CoreInstance.objects.get(
                    provider_alias=instance_id,
                    source__provider__uuid=provider_uuid,
                    created_by_identity__uuid=identity_uuid)
                core_inst.end_date_all()
            except CoreInstance.DoesNotExist:
                pass
            return instance_not_found(instance_id)

        core_instance = convert_esh_instance(esh_driver, esh_instance,
                                             provider_uuid, identity_uuid,
                                             user)
        serialized_data = InstanceSerializer(
            core_instance,
            context={"request": request}).data
        response = Response(serialized_data)
        response['Cache-Control'] = 'no-cache'
        return response

    def patch(self, request, provider_uuid, identity_uuid, instance_id):
        """Authentication Required, update metadata about the instance"""
        user = request.user
        data = request.data
        esh_driver = prepare_driver(request, provider_uuid, identity_uuid)
        if not esh_driver:
            return invalid_creds(provider_uuid, identity_uuid)
        try:
            esh_instance = esh_driver.get_instance(instance_id)
        except (socket_error, ConnectionFailure):
            return connection_failure(provider_uuid, identity_uuid)
        except LibcloudInvalidCredsError:
            return invalid_creds(provider_uuid, identity_uuid)
        except Exception as exc:
            logger.exception("Encountered a generic exception. "
                             "Returning 409-CONFLICT")
            return failure_response(status.HTTP_409_CONFLICT,
                                    str(exc.message))
        if not esh_instance:
            return instance_not_found(instance_id)
        # Gather the DB related item and update
        core_instance = convert_esh_instance(esh_driver, esh_instance,
                                             provider_uuid, identity_uuid,
                                             user)
        serializer = InstanceSerializer(
            core_instance, data=data,
            context={"request": request}, partial=True)
        identity = Identity.objects.get(uuid=identity_uuid)
        provider = identity.provider

        if serializer.is_valid():
            logger.info('metadata = %s' % data)

            driver_class = esh_driver.__class__
            update_metadata.s(driver_class, provider, identity, esh_instance.id,
                              data, replace_metadata=False).apply()
            instance = serializer.save()
            boot_scripts = data.pop('boot_scripts', [])
            if boot_scripts:
                _save_scripts_to_instance(instance, boot_scripts)
            invalidate_cached_instances(identity=identity)
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
        data = request.data
        # Ensure item exists on the server first
        esh_driver = prepare_driver(request, provider_uuid, identity_uuid)
        if not esh_driver:
            return invalid_creds(provider_uuid, identity_uuid)
        try:
            esh_instance = esh_driver.get_instance(instance_id)
        except (socket_error, ConnectionFailure):
            return connection_failure(provider_uuid, identity_uuid)
        except LibcloudInvalidCredsError:
            return invalid_creds(provider_uuid, identity_uuid)
        except Exception as exc:
            logger.exception("Encountered a generic exception. "
                             "Returning 409-CONFLICT")
            return failure_response(status.HTTP_409_CONFLICT,
                                    str(exc.message))
        if not esh_instance:
            return instance_not_found(instance_id)
        # Gather the DB related item and update
        core_instance = convert_esh_instance(esh_driver, esh_instance,
                                             provider_uuid, identity_uuid,
                                             user)
        serializer = InstanceSerializer(core_instance, data=data,
                                        context={"request": request})
        identity = Identity.objects.get(uuid=identity_uuid)
        if serializer.is_valid():
            logger.info('metadata = %s' % data)
            #NOTE: We shouldn't allow 'full replacement' of metadata..
            # We should also validate against potentional updating of 'atmo-used metadata'
            update_metadata.s(esh_driver.__class__, esh_driver.provider, esh_driver.identity, esh_instance.id,
                              data, replace_metadata=False).apply()
            new_instance = serializer.save()
            boot_scripts = data.pop('boot_scripts', [])
            if boot_scripts:
                new_instance = _save_scripts_to_instance(new_instance,
                                                         boot_scripts)
                serializer = InstanceSerializer(
                    new_instance,
                    context={"request": request})
            invalidate_cached_instances(identity=identity)
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
        except (socket_error, ConnectionFailure):
            return connection_failure(provider_uuid, identity_uuid)
        except LibcloudInvalidCredsError:
            return invalid_creds(provider_uuid, identity_uuid)
        except Exception as exc:
            logger.exception("Encountered a generic exception. "
                             "Returning 409-CONFLICT")
            return failure_response(status.HTTP_409_CONFLICT,
                                    str(exc.message))
        try:
            # Test that there is not an attached volume BEFORE we destroy
            task.destroy_instance_task(user, esh_instance, identity_uuid)

            invalidate_cached_instances(
                identity=Identity.objects.get(uuid=identity_uuid))

            existing_instance = esh_driver.get_instance(instance_id)
            if existing_instance:
                # Instance will be deleted soon...
                esh_instance = existing_instance
                if esh_instance.extra\
                   and 'task' not in esh_instance.extra:
                    esh_instance.extra['task'] = 'queueing delete'
        except VolumeAttachConflict as exc:
            message = exc.message
            return failure_response(status.HTTP_409_CONFLICT, message)
        except (socket_error, ConnectionFailure):
            return connection_failure(provider_uuid, identity_uuid)
        except LibcloudInvalidCredsError:
            return invalid_creds(provider_uuid, identity_uuid)
        except InstanceDoesNotExist as dne:
            return failure_response(
                status.HTTP_404_NOT_FOUND,
                'Instance %s no longer exists' % (dne.message,))
        except Exception as exc:
            logger.exception("Encountered a generic exception. "
                             "Returning 409-CONFLICT")
            return failure_response(status.HTTP_409_CONFLICT,
                                    str(exc.message))

        try:
            core_instance = convert_esh_instance(esh_driver, esh_instance,
                                                 provider_uuid, identity_uuid,
                                                 user)
            if core_instance:
                core_instance.end_date_all()
            else:
                logger.warn("Unable to find core instance %s." % (instance_id))
            serialized_data = InstanceSerializer(
                core_instance,
                context={"request": request}).data
            response = Response(serialized_data, status=status.HTTP_200_OK)
            response['Cache-Control'] = 'no-cache'
            return response
        except (Identity.DoesNotExist) as exc:
            return failure_response(status.HTTP_400_BAD_REQUEST,
                                    "Invalid provider_uuid or identity_uuid.")
        except (socket_error, ConnectionFailure):
            return connection_failure(provider_uuid, identity_uuid)
        except LibcloudInvalidCredsError:
            return invalid_creds(provider_uuid, identity_uuid)


class InstanceTagList(AuthAPIView):

    """
    Tags are a easy way to allow users to group several images as similar
    based on a feature/program of the application.
    """

    def get(self, request, provider_uuid, identity_uuid, instance_id,
            *args, **kwargs):
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
        data = request.data.copy()
        if 'name' not in data:
            return Response("Missing 'name' in POST data",
                            status=status.HTTP_400_BAD_REQUEST)

        core_instance = get_core_instance(request,
                                          provider_uuid,
                                          identity_uuid,
                                          instance_id)
        if not core_instance:
            instance_not_found(instance_id)

        same_name_tags = CoreTag.objects.filter(name__iexact=data['name'])
        if same_name_tags:
            add_tag = same_name_tags[0]
        else:
            data['user'] = user.username
            data['name'] = data['name'].lower()
            serializer = TagSerializer(data=data)
            if not serializer.is_valid():
                return Response(
                    serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            add_tag = serializer.save()
        core_instance.tags.add(add_tag)
        return Response(status=status.HTTP_204_NO_CONTENT)


class InstanceTagDetail(AuthAPIView):

    """
    Tags are a easy way to allow users to group several images as similar
    based on a feature/program of the application.

    This API resource allows you to Retrieve, Update, or Delete your Tag.
    """

    def delete(self, request, provider_uuid, identity_uuid, instance_id,
               tag_slug, *args, **kwargs):
        """
        Remove the tag, if it is no longer in use.
        """
        core_instance = get_core_instance(request, provider_uuid,
                                          identity_uuid, instance_id)
        if not core_instance:
            instance_not_found(instance_id)
        try:
            tag = core_instance.tags.get(name__iexact=tag_slug)
        except CoreTag.DoesNotExist:
            return failure_response(
                status.HTTP_404_NOT_FOUND,
                'Tag %s not found on instance' % tag_slug)
        core_instance.tags.remove(tag)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get(self, request, provider_uuid, identity_uuid, instance_id,
            tag_slug, *args, **kwargs):
        """
        Return the credential information for this tag
        """
        try:
            core_instance = get_core_instance(request, provider_uuid,
                                              identity_uuid, instance_id)
        except ProviderNotActive as pna:
            return inactive_provider(pna)
        except Exception as e:
            return failure_response(
                status.HTTP_409_CONFLICT,
                e.message)

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
    return [key for key in required
            if key not in data or
            (isinstance(data[key], str) and len(data[key]) > 0)]


def keys_not_found(missing_keys):
    return failure_response(
        status.HTTP_400_BAD_REQUEST,
        'Missing data for variable(s): %s' % missing_keys)
