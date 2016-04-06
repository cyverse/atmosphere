from core.models.provider import Provider, ProviderType, ProviderInstanceAction
from core.models.instance_action import InstanceAction
from rest_framework import serializers


class ProviderSerializer(serializers.ModelSerializer):
    type = serializers.SlugRelatedField(
        slug_field='name',
        queryset=ProviderType.objects.all())
    location = serializers.CharField(source='get_location')
    id = serializers.CharField(source='uuid')

    class Meta:
        model = Provider
        exclude = ('active', 'start_date', 'end_date', 'uuid')


class ProviderInstanceActionSerializer(serializers.ModelSerializer):
    provider = serializers.SlugRelatedField(
        slug_field="location",
        queryset=Provider.objects.all())
    instance_action = serializers.SlugRelatedField(
        slug_field="name",
        queryset=InstanceAction.objects.all())

    class Meta:
        model = ProviderInstanceAction


class PATCH_ProviderInstanceActionSerializer(ProviderInstanceActionSerializer):

    def update(self, instance, validated_data):
        instance.enabled = validated_data.get('enabled', instance.enabled)
        instance.save()
        return instance


class POST_ProviderInstanceActionSerializer(ProviderInstanceActionSerializer):

    """
    Override create here..
    """
    provider = serializers.SlugRelatedField(
        slug_field="uuid",
        queryset=Provider.objects.all())
    instance_action = serializers.SlugRelatedField(
        slug_field="id",
        queryset=InstanceAction.objects.all())
    pass
