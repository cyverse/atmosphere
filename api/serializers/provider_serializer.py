from core.models.provider import Provider, ProviderType
from rest_framework import serializers


class ProviderSerializer(serializers.ModelSerializer):
    type = serializers.SlugRelatedField(slug_field='name', queryset=ProviderType.objects.all())
    location = serializers.CharField(source='get_location')
    id = serializers.CharField(source='uuid')
    #membership = serializers.Field(source='get_membership')

    class Meta:
        model = Provider
        exclude = ('active', 'start_date', 'end_date', 'uuid')

class InstanceActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderInstanceAction
