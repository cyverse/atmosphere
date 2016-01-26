import django_filters
import pytz
from django.utils import timezone
from libcloud.common.types import InvalidCredsError, MalformedResponseError
from rest_framework import exceptions
from rest_framework.decorators import detail_route
from rest_framework.response import Response
from rest_framework import status

from api.exceptions import (inactive_provider)
from api.v2.serializers.details import VolumeSerializer, UpdateVolumeSerializer
from api.v2.views.base import AuthViewSet
from api.v2.views.mixins import MultipleFieldLookup

from core.exceptions import ProviderNotActive
from core.models.volume import Volume, find_volume
from core.query import only_current_source
from service.volume import create_volume_or_fail, destroy_volume_or_fail, update_volume_metadata
from service.exceptions import OverQuotaError
from rtwo.exceptions import ConnectionFailure
from threepio import logger

UPDATE_METHODS = ("PUT", "PATCH")

VOLUME_EXCEPTIONS = (OverQuotaError, ConnectionFailure, MalformedResponseError)


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

    def perform_create(self, serializer):
        data = serializer.validated_data
        name = data.get('name')
        size = data.get('size')
        image_id = data.get('image_id')
        snapshot_id = data.get('snapshot_id')
        description = data.get('description')
        instance_source = data.get("instance_source")
        identity = instance_source.get("created_by_identity")
        provider = identity.provider
        try:
            esh_volume = create_volume_or_fail(name, size, self.request.user,
                                               provider, identity,
                                               description=description,
                                               image_id=image_id,
                                               snapshot_id=snapshot_id)
            created_on = esh_volume.extra.get("createTime", timezone.now())
            serializer.save(identifier=esh_volume.id,
                            name=esh_volume.name,
                            created_on=pytz.utc.localize(created_on),
                            user=self.request.user)
        except InvalidCredsError as e:
            raise exceptions.PermissionDenied(detail=e.message)
        except ProviderNotActive as pna:
            return inactive_provider(pna)
        except VOLUME_EXCEPTIONS as e:
            raise exceptions.ParseError(detail=e.message)
        except Exception as exc:
            logger.exception("Error occurred creating a v2 volume")
            return Response(exc.message, status=status.HTTP_409_CONFLICT)

    def perform_destroy(self, instance):
        try:
            destroy_volume_or_fail(instance, self.request.user)
            instance.end_date = timezone.now()
            instance.save()
        except InvalidCredsError as e:
            raise exceptions.PermissionDenied(detail=e.message)
        except ProviderNotActive as pna:
            return inactive_provider(pna)
        except VOLUME_EXCEPTIONS as e:
            raise exceptions.ParseError(detail=e.message)
