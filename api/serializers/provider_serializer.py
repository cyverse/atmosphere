from core.models.provider import Provider, ProviderType, ProviderInstanceAction
from core.models.instance import InstanceAction
from rest_framework import serializers


class ProviderSerializer(serializers.ModelSerializer):
    type = serializers.SlugRelatedField(slug_field='name', queryset=ProviderType.objects.all())
    location = serializers.CharField(source='get_location')
    id = serializers.CharField(source='uuid')
    #membership = serializers.Field(source='get_membership')

    class Meta:
        model = Provider
        exclude = ('active', 'start_date', 'end_date', 'uuid')


class ProviderInstanceActionSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProviderInstanceAction


class PATCH_ProviderInstanceActionSerializer(ProviderInstanceActionSerializer):
    def update(self, instance, validated_data):
        instance.enabled = validated_data.get('enabled', instance.enabled)
        return instance

class POST_ProviderInstanceActionSerializer(ProviderInstanceActionSerializer):
    provider = serializers.SlugRelatedField(slug_field="uuid", queryset=Provider.objects.all())
    instance_action = serializers.SlugRelatedField(slug_field="id", queryset=InstanceAction.objects.all())
