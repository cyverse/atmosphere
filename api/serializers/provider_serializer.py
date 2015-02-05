from core.models.provider import Provider, ProviderType, Trait
from rest_framework import serializers


class ProviderSerializer(serializers.ModelSerializer):
    type = serializers.SlugRelatedField(slug_field='name', queryset=ProviderType.objects.all())
    location = serializers.CharField(source='get_location')
    # traits = serializers.RelatedField(source='traits.all', many=True, queryset=Trait.objects.all())
    id = serializers.CharField(source='uuid')
    #membership = serializers.Field(source='get_membership')

    class Meta:
        model = Provider
        exclude = ('active', 'start_date', 'end_date', 'uuid', 'traits')