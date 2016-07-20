import django_filters
import pytz
from django.utils import timezone
from rtwo.exceptions import LibcloudInvalidCredsError, LibcloudBadResponseError, ConnectionFailure
from rest_framework import exceptions
from rest_framework.decorators import detail_route
from rest_framework.response import Response
from rest_framework import status

from api.exceptions import (inactive_provider)
from api.v2.serializers.details import VolumeSerializer, UpdateVolumeSerializer
from api.v2.serializers.post import VolumeSerializer as POSTVolumeSerializer
from api.v2.views.base import AuthViewSet
from api.v2.views.mixins import MultipleFieldLookup

from core.exceptions import ProviderNotActive
from core.models.volume import Volume, find_volume
from core.query import only_current_source
from service.volume import create_volume_or_fail, destroy_volume_or_fail, update_volume_metadata
from service.exceptions import OverQuotaError
from threepio import logger

UPDATE_METHODS = ("PUT", "PATCH")
CREATE_METHODS = ("POST",)

VOLUME_EXCEPTIONS = (OverQuotaError, ConnectionFailure, LibcloudBadResponseError)


class VolumeFilter(django_filters.FilterSet):
    min_size = django_filters.NumberFilter(name="size", lookup_type='gte')
    max_size = django_filters.NumberFilter(name="size", lookup_type='lte')

    class Meta:
        model = Volume
        fields = ['min_size', 'max_size', 'projects']


class VolumeViewSet(MultipleFieldLookup, AuthViewSet):

    """
    API endpoint that allows providers to be viewed or edited.
    """
    lookup_fields = ("id", "instance_source__identifier")
    serializer_class = VolumeSerializer
    filter_class = VolumeFilter
    http_method_names = ('get', 'post', 'put', 'patch', 'delete',
                         'head', 'options', 'trace')

    def get_serializer_class(self):
        if self.request.method in UPDATE_METHODS:
            return UpdateVolumeSerializer
        elif self.request.method in CREATE_METHODS:
            return POSTVolumeSerializer
        return self.serializer_class

    def get_queryset(self):
        """
        Filter projects by current user
        """
        user = self.request.user
        identity_ids = user.current_identities.values_list('id',flat=True)
        return Volume.objects.filter(
            only_current_source(),
            instance_source__created_by_identity__in=identity_ids)

    @detail_route(methods=['post'])
    def update_metadata(self, request, pk=None):
        """
        Until a better method comes about, we will handle Updating metadata here.
        """
        data = request.data
        metadata = data.pop('metadata')
        volume_id = pk
        volume = find_volume(volume_id)
        try:
            update_volume_metadata(volume, metadata)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as exc:
            logger.exception("Error occurred updating v2 volume metadata")
            return Response(exc.message, status=status.HTTP_409_CONFLICT)

    def create(self, request):
        """
        Override 'create' at a higher level than 'perform_create'
        so that we can swap Serializers behind-the-scenes.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        #NOTE: This work normally happens in 'perform_create()'
        data = serializer.validated_data
        name = data.get('name')
        size = data.get('size')
        image_id = data.get('image_id')
        snapshot_id = data.get('snapshot_id')
        description = data.get('description')
        project = data.get('projects')
        identity = data.get("created_by_identity")
        provider = identity.provider
        try:
            core_volume = create_volume_or_fail(
                name, size, self.request.user,
                provider, identity,
                description=description,
                project=project,
                image_id=image_id,
                snapshot_id=snapshot_id)
            #NOTE: This is normally where 'perform_create()' would end
            # but we swap out the VolumeSerializer Class at this point.
            serialized_volume = VolumeSerializer(
                core_volume, context={'request': self.request},
                data={}, partial=True)
            if not serialized_volume.is_valid():
                return Response(serialized_volume.errors,
                                status=status.HTTP_400_BAD_REQUEST)
            serialized_volume.save()
            headers = self.get_success_headers(serialized_volume.data)
            return Response(
                serialized_volume.data, status=status.HTTP_201_CREATED, headers=headers)
        except LibcloudInvalidCredsError as e:
            raise exceptions.PermissionDenied(detail=e.message)
        except ProviderNotActive as pna:
            return inactive_provider(pna)
        except VOLUME_EXCEPTIONS as e:
            raise exceptions.ParseError(detail=e.message)
        except Exception as exc:
            logger.exception("Error occurred creating a v2 volume -- User:%s"
                             % self.request.user)
            return Response(exc.message, status=status.HTTP_409_CONFLICT)

    def perform_destroy(self, instance):
        try:
            destroy_volume_or_fail(instance, self.request.user)
            instance.end_date = timezone.now()
            instance.save()
        except LibcloudInvalidCredsError as e:
            raise exceptions.PermissionDenied(detail=e.message)
        except ProviderNotActive as pna:
            return inactive_provider(pna)
        except VOLUME_EXCEPTIONS as e:
            raise exceptions.ParseError(detail=e.message)
        except Exception as exc:
            logger.exception("Error occurred deleting a v2 volume -- User:%s"
                             % self.request.user)
            return Response(exc.message, status=status.HTTP_409_CONFLICT)
