from api.v2.serializers.details import InstanceSerializer
from api.v2.serializers.post import InstanceSerializer as POST_InstanceSerializer
from api.v2.views.base import AuthViewSet
from api.v2.views.mixins import MultipleFieldLookup
from core.models import Instance
from core.models.boot_script import _save_scripts_to_instance
from core.query import only_current
from rest_framework import status
from rest_framework.response import Response
from service.instance import launch_instance
from service.task import destroy_instance_task
from threepio import logger

#Things that go bump
from api.exceptions import failure_response, invalid_creds, connection_failure, over_quota, under_threshold, size_not_available, over_capacity
from libcloud.common.types import InvalidCredsError, MalformedResponseError
from service.exceptions import OverAllocationError, OverQuotaError,\
    SizeNotAvailable, HypervisorCapacityError, SecurityGroupNotCreated,\
    UnderThresholdError
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
    http_method_names = ['get', 'put', 'patch', 'post', 'head', 'options', 'trace']

    def get_serializer_class(self):
        if self.action != 'create':
            return InstanceSerializer
        return POST_InstanceSerializer

    def get_queryset(self):
        """
        Filter projects by current user.
        """
        user = self.request.user
        if 'archived' in self.request.query_params:
            return Instance.objects.filter(created_by=user)
        return Instance.objects.filter(only_current(), created_by=user)

    def perform_destroy(self, instance):
        try:
            # Test that there is not an attached volume BEFORE we destroy
            #NOTE: Although this is a task we are calling and waiting for response..
            destroy_instance_task(esh_instance, identity_uuid).get()
        except VolumeAttachConflict as exc:
            message = exc.message
            return failure_response(status.HTTP_409_CONFLICT, message)
        except (socket_error, ConnectionFailure):
            return connection_failure(provider_uuid, identity_uuid)
        except InvalidCredsError:
            return invalid_creds(provider_uuid, identity_uuid)
        except Exception as exc:
            logger.exception("Encountered a generic exception. "
                             "Returning 409-CONFLICT")
            return failure_response(status.HTTP_409_CONFLICT,
                                    str(exc.message))
        return super(InstanceViewSet, self).perform_destroy(instance)

    def perform_create(self, serializer):
        data = serializer.data
        user = self.request.user

        name = data.get('name')
        boot_scripts = data.pop("scripts", [])
        identity_uuid = data.get('identity')
        source_alias = data.get('source_alias')
        size_alias = data.get('size_alias')
        deploy = data.get('deploy')
        extra = data.get('extra')
        try:
            core_instance = launch_instance(
                user, identity_uuid, size_alias, source_alias, name, deploy,
                **extra)
            # Faking a 'partial update of nothing' to allow call to 'is_valid'
            serialized_instance = InstanceSerializer(core_instance, context={'request':self.request}, data={}, partial=True)
            if not serialized_instance.is_valid():
                return Response(serializer.errors,
                                status=status.HTTP_400_BAD_REQUEST)
            instance = serialized_instance.save()
            if boot_scripts:
                _save_scripts_to_instance(instance, boot_scripts)
        except UnderThresholdError as ute:
            return under_threshold(ute)
        except OverQuotaError as oqe:
            return over_quota(oqe)
        except OverAllocationError as oae:
            return over_quota(oae)
        except SizeNotAvailable as snae:
            return size_not_available(snae)
        except HypervisorCapacityError as hce:
            return over_capacity(hce)
        except SecurityGroupNotCreated:
            return connection_failure(provider_uuid, identity_uuid)
        except (socket_error, ConnectionFailure):
            return connection_failure(provider_uuid, identity_uuid)
        except InvalidCredsError:
            return invalid_creds(provider_uuid, identity_uuid)
        except Exception as exc:
            logger.exception("Encountered a generic exception. "
                             "Returning 409-CONFLICT")
            return failure_response(status.HTTP_409_CONFLICT,
                                    str(exc.message))

