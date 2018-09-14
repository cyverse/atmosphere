from rest_framework import serializers
from core.serializers.fields import ModelRelatedField
from core.models import (
    AllocationSource, Instance, InstanceAllocationSourceSnapshot
)
from rest_framework.validators import UniqueTogetherValidator
from api.v2.serializers.details import (
    AllocationSourceSerializer, InstanceSerializer
)


class InstanceAllocationSourceSerializer(
    serializers.HyperlinkedModelSerializer
):
    allocation_source = ModelRelatedField(
        queryset=AllocationSource.objects.all(),
        serializer_class=AllocationSourceSerializer,
        style={'base_template': 'input.html'}
    )
    instance = ModelRelatedField(
        queryset=Instance.objects.all(),
        serializer_class=InstanceSerializer,
        style={'base_template': 'input.html'}
    )
    url = serializers.HyperlinkedIdentityField(
        view_name='api:v2:instance-allocation-source-detail',
    )

    class Meta:
        model = InstanceAllocationSourceSnapshot
        validators = [
            UniqueTogetherValidator(
                queryset=InstanceAllocationSourceSnapshot.objects.all(),
                fields=('instance', 'allocation_source')
            ),
        ]
        fields = ('id', 'url', 'instance', 'allocation_source')
