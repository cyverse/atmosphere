from api.v2.serializers.details import InstanceSerializer, InstanceActionSerializer
from api.v2.serializers.post import InstanceSerializer as POST_InstanceSerializer
from api.v2.views.base import AuthViewSet
from api.v2.views.mixins import MultipleFieldLookup
from api.v2.views.instance_action import InstanceActionViewSet

from core.exceptions import ProviderNotActive
from core.models import Instance, Identity, AllocationSource, EventTable
from core.models.boot_script import _save_scripts_to_instance
from core.models.instance import find_instance
from core.models.instance_action import InstanceAction
from core.query import only_current

from rest_framework import status
from rest_framework import renderers
from rest_framework.decorators import detail_route, renderer_classes
from rest_framework.response import Response

from service.instance import (
    launch_instance, destroy_instance, run_instance_action,
    update_instance_metadata)
from threepio import logger
# Things that go bump
from api.v2.exceptions import (
    failure_response, invalid_creds, connection_failure)
from api.exceptions import (
    over_quota, under_threshold, size_not_available,
    over_capacity, mount_failed, inactive_provider)
from rtwo.exceptions import LibcloudInvalidCredsError
from service.exceptions import (
    ActionNotAllowed, OverAllocationError, OverQuotaError,
    SizeNotAvailable, HypervisorCapacityError, SecurityGroupNotCreated,
    UnderThresholdError, VolumeAttachConflict, VolumeMountConflict,
    InstanceDoesNotExist)
from socket import error as socket_error
from rtwo.exceptions import ConnectionFailure


class InstanceViewSet(MultipleFieldLookup, AuthViewSet):

    """
    API endpoint that allows providers to be viewed or edited.
    """

    queryset = Instance.objects.all()
    serializer_class = InstanceSerializer
    filter_fields = ('created_by__id', 'projects')
    lookup_fields = ("id", "provider_alias")
    http_method_names = ['get', 'put', 'patch', 'post',
                         'delete', 'head', 'options', 'trace']

    def get_serializer_class(self):
        if self.action == 'create':
            return POST_InstanceSerializer
        elif self.action == 'actions':
            return InstanceActionSerializer
        return InstanceSerializer

    def get_queryset(self):
        """
        Filter projects by current user.
        """
        user = self.request.user
        qs = Instance.for_user(user)
        if 'archived' in self.request.query_params:
            return qs
        return qs.filter(only_current())

    @detail_route(methods=['post'])
    def update_metadata(self, request, pk=None):
        """
        Until a better method comes about,
        we will handle Updating metadata here.
        """
        data = request.data.copy()
        metadata = data.pop('metadata')
        instance_id = pk
        instance = find_instance(instance_id)
        try:
            update_instance_metadata(instance, metadata)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as exc:
            logger.exception("Error occurred updating v2 instance metadata")
            return Response(exc.message, status=status.HTTP_409_CONFLICT)

    @detail_route(methods=['get', 'post'])
    def actions(self, request, pk=None):
        """
        Until a better method comes about, we will handle InstanceActions here.
        """
        method = request.method
        if method == 'GET':
            return self.list_instance_actions(request, pk=pk)
        return self.post_instance_action(request, pk=pk)

    def list_instance_actions(self, request, pk=None):
        valid_actions = InstanceAction.filter_by_instance(pk)
        serializer_class = self.get_serializer_class()
        serialized_data = serializer_class(
            valid_actions, many=True,
            context={'request': request}).data
        return Response(serialized_data)

    def post_instance_action(self, request, pk=None):
        user = request.user
        instance_id = pk
        instance = find_instance(instance_id)
        identity = instance.created_by_identity
        action_params = request.data
        action = action_params.pop('action')
        try:
            result_obj = run_instance_action(user, identity, instance_id, action, action_params)
            api_response = {
                'result': 'success',
                'message': 'The requested action <%s> was run successfully' % (action,),
                'object': result_obj,
            }
            response = Response(api_response, status=status.HTTP_200_OK)
            return response
        except (socket_error, ConnectionFailure):
            return connection_failure(identity)
        except InstanceDoesNotExist as dne:
            return failure_response(
                status.HTTP_404_NOT_FOUND,
                'Instance %s no longer exists' % (dne.message,))
        except LibcloudInvalidCredsError:
            return invalid_creds(identity)
        except HypervisorCapacityError as hce:
            return over_capacity(hce)
        except ProviderNotActive as pna:
            return inactive_provider(pna)
        except (OverQuotaError, OverAllocationError) as oqe:
            return over_quota(oqe)
        except SizeNotAvailable as snae:
            return size_not_available(snae)
        except (socket_error, ConnectionFailure):
            return connection_failure(identity)
        except LibcloudInvalidCredsError:
            return invalid_creds(identity)
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

    def perform_destroy(self, instance):
        user = self.request.user
        identity_uuid = instance.created_by_identity.uuid
        identity = Identity.objects.get(uuid=identity_uuid)
        try:
            # Test that there is not an attached volume BEFORE we destroy
            #NOTE: Although this is a task we are calling and waiting for response..
            core_instance = destroy_instance(
                user,
                identity_uuid,
                instance.provider_alias)
            serialized_instance = InstanceSerializer(
                core_instance, context={
                    'request': self.request},
                data={}, partial=True)
            if not serialized_instance.is_valid():
                return Response(serialized_instance.data,
                                status=status.HTTP_400_BAD_REQUEST)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except VolumeAttachConflict as exc:
            message = exc.message
            return failure_response(status.HTTP_409_CONFLICT, message)
        except (socket_error, ConnectionFailure):
            return connection_failure(identity)
        except LibcloudInvalidCredsError:
            return invalid_creds(identity)
        except Exception as exc:
            logger.exception("Encountered a generic exception. "
                             "Returning 409-CONFLICT")
            return failure_response(status.HTTP_409_CONFLICT,
                                    str(exc.message))

    def validate_input(self, user, data):
        error_map = {}

        name = data.get('name')
        identity_uuid = data.get('identity')
        source_alias = data.get('source_alias')
        size_alias = data.get('size_alias')
        allocation_source_id = data.get('allocation_source_id')
        if not name:
            error_map['name'] = "This field is required."
        if not identity_uuid:
            error_map['identity'] = "This field is required."
        if not source_alias:
            error_map['source_alias'] = "This field is required."
        if not size_alias:
            error_map['size_alias'] = "This field is required."
        if not allocation_source_id:
            error_map['allocation_source_id'] = "This field is required."

        if error_map:
            raise Exception(error_map)

        try:
            identity = Identity.objects.get(uuid=identity_uuid)
            # Staff or owner ONLY
            if not user.is_staff and identity.created_by != user:
                logger.error("User %s does not have permission to use identity %s" % (user, identity))
                raise Identity.DoesNotExist("You are not the owner")
        except Identity.DoesNotExist:
            error_map["identity"] = "The uuid (%s) is invalid." % identity_uuid
            raise Exception(error_map)
        return

    def create(self, request):
        user = request.user
        data = request.data
        try:
            self.validate_input(user, data)
        except Exception as exc:
            return failure_response(
                status.HTTP_400_BAD_REQUEST,
                exc.message)

        # Create a mutable dict and start modifying.
        data = data.copy()
        name = data.get('name')
        identity_uuid = data.get('identity')
        source_alias = data.get('source_alias')
        size_alias = data.get('size_alias')
        allocation_source_id = data.get('allocation_source_id')
        boot_scripts = data.pop("scripts", [])
        deploy = data.get('deploy')
        extra = data.get('extra')
        try:
            identity = Identity.objects.get(uuid=identity_uuid)
            allocation_source = AllocationSource.objects.get(source_id=allocation_source_id)
            core_instance = launch_instance(
                user, identity_uuid, size_alias, source_alias, name, deploy,
                **extra)
            # Faking a 'partial update of nothing' to allow call to 'is_valid'
            serialized_instance = InstanceSerializer(
                core_instance, context={'request': self.request},
                data={}, partial=True)
            if not serialized_instance.is_valid():
                return Response(serialized_instance.errors,
                                status=status.HTTP_400_BAD_REQUEST)
            instance = serialized_instance.save()
            if boot_scripts:
                _save_scripts_to_instance(instance, boot_scripts)
            instance.change_allocation_source(allocation_source)
            return Response(
                serialized_instance.data, status=status.HTTP_201_CREATED)
        except UnderThresholdError as ute:
            return under_threshold(ute)
        except (OverQuotaError, OverAllocationError) as oqe:
            return over_quota(oqe)
        except ProviderNotActive as pna:
            return inactive_provider(pna)
        except SizeNotAvailable as snae:
            return size_not_available(snae)
        except HypervisorCapacityError as hce:
            return over_capacity(hce)
        except SecurityGroupNotCreated:
            return connection_failure(identity)
        except (socket_error, ConnectionFailure):
            return connection_failure(identity)
        except LibcloudInvalidCredsError:
            return invalid_creds(identity)
        except Exception as exc:
            logger.exception("Encountered a generic exception. "
                             "Returning 409-CONFLICT")
            return failure_response(status.HTTP_409_CONFLICT,
                                    str(exc.message))

