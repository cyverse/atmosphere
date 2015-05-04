from core.models import Application as Image
from rest_framework import serializers
from api.v2.serializers.summaries import TagSummarySerializer, UserSummarySerializer
from api.v2.serializers.fields import ProviderMachineRelatedField


class ImageSerializer(serializers.HyperlinkedModelSerializer):
    created_by = UserSummarySerializer()
    tags = TagSummarySerializer(many=True)
    provider_images = ProviderMachineRelatedField(source='all_machines', many=True)

    class Meta:
        model = Image
        view_name = 'api_v2:application-detail'
        fields = (
            'id', 'url', 'uuid', 'name', 'description', 'icon', 'created_by',
            'tags', 'start_date', 'end_date', 'provider_images'
        )
