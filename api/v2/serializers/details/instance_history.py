from rest_framework import serializers

from core.models import Instance, InstanceStatusHistory, Size, Provider, Application as Image

from api.v2.serializers.summaries import (
    InstanceSuperSummarySerializer, ProviderSummarySerializer, ImageSummarySerializer)
from api.v2.serializers.summaries.size import SizeRelatedField
from api.v2.serializers.fields import ModelRelatedField

class InstanceRelatedField(serializers.PrimaryKeyRelatedField):

    def to_representation(self, value):
        instance = Instance.objects.get(pk=value.pk)
        # important! We have to use the SuperSummary because there are non-end_dated
        # instances that don't have a valid size (size='Unknown')
        serializer = InstanceSuperSummarySerializer(
            instance,
            context=self.context)
        return serializer.data

class InstanceStatusHistorySerializer(serializers.HyperlinkedModelSerializer):
    instance = InstanceRelatedField(queryset=Instance.objects.none())
    size = SizeRelatedField(queryset=Size.objects.none())
    provider = ModelRelatedField(
        source='instance.provider_machine.provider',
        queryset=Provider.objects.all(),
        serializer_class=ProviderSummarySerializer,
        style={'base_template': 'input.html'})
    image = ModelRelatedField(
        source='instance.provider_machine.application_version.application',
        queryset=Image.objects.all(),
        serializer_class=ImageSummarySerializer,
        style={'base_template': 'input.html'})
    status = serializers.SlugRelatedField(slug_field='name', read_only=True)

    class Meta:
        model = InstanceStatusHistory
        view_name = 'api:v2:instancestatushistory-detail'
        fields = (
            'id',
            'url',
            'instance',
            'status',
            'size',
            'provider',
            'image',
            'start_date',
            'end_date',
        )
