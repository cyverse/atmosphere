from core.models import Provider, ProviderType, PlatformType
from rest_framework import serializers
from api.v2.serializers.summaries import SizeSummarySerializer
from api.v2.serializers.fields.base import DebugHyperlinkedIdentityField, UUIDHyperlinkedIdentityField 

class ProviderTypeSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='api:v2:providertype-detail',
    )

    class Meta:
        model = ProviderType
        fields = ('id', 'url', 'name', 'start_date', 'end_date')


class PlatformTypeSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='api:v2:platformtype-detail',
    )

    class Meta:
        model = PlatformType
        fields = ('id', 'url', 'name', 'start_date', 'end_date')


class ProviderSerializer(serializers.HyperlinkedModelSerializer):
    name = serializers.CharField(source='location')
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:provider-detail',
    )
    type = ProviderTypeSerializer()
    virtualization = PlatformTypeSerializer()
    sizes = SizeSummarySerializer(source='size_set', many=True)
    is_admin = serializers.SerializerMethodField()

    def get_is_admin(self, provider):
        user = self.context['request'].user
        if user.is_staff or user.is_superuser:
            return True
        return False

    class Meta:
        model = Provider
        fields = (
            'id',
            'url',
            'uuid',
            'name',
            'description',
            'type',
            'virtualization',
            'active',
            'public',
            'auto_imaging',
            'sizes',
            'start_date',
            'end_date',
            'is_admin',
        )
