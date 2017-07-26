from rest_framework import serializers
from api.v2.serializers.fields import ModelRelatedField
from core.models import (
    AllocationSource, AtmosphereUser, UserAllocationSource
)
from rest_framework.validators import UniqueTogetherValidator
from api.v2.serializers.details import (
    AllocationSourceSerializer, UserSerializer
)


class UserAllocationSourceSerializer(serializers.HyperlinkedModelSerializer):
    allocation_source = ModelRelatedField(
        queryset=AllocationSource.objects.all(),
        serializer_class= AllocationSourceSerializer,
        style={'base_template': 'input.html'})
    user = ModelRelatedField(
        queryset=AtmosphereUser.objects.all(),
        serializer_class=UserSerializer,
        style={'base_template': 'input.html'})
    url = serializers.HyperlinkedIdentityField(
        view_name='api:v2:user-allocation-source-detail',
    )

    class Meta:
        model = UserAllocationSource
        validators = [
            UniqueTogetherValidator(
                queryset=UserAllocationSource.objects.all(),
                fields=('user', 'allocation_source')
                ),
        ]
        fields = (
            'id',
            'url',
            'user',
            'allocation_source'
        )
