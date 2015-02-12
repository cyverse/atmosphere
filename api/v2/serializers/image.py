from core.models import Application as Image, ApplicationBookmark as ImageBookmark
from rest_framework import serializers
from .user import UserSerializer
from .tag import TagSerializer
from .provider_machine import ProviderMachineSummarySerializer


class MachineProviderRelatedField(serializers.RelatedField):

    def __init__(self, **kwargs):
        kwargs['read_only'] = True
        super(MachineProviderRelatedField, self).__init__(**kwargs)

    def to_representation(self, value):
        serializer = ProviderMachineSummarySerializer(value, context=self.context)
        return serializer.data


class ImageSerializer(serializers.HyperlinkedModelSerializer):
    created_by = UserSerializer()
    tags = TagSerializer(many=True)
    provider_images = MachineProviderRelatedField(source='providermachine_set', many=True)

    class Meta:
        model = Image
        view_name = 'api_v2:application-detail'
        fields = ('id', 'url', 'uuid', 'name', 'description', 'icon', 'created_by', 'tags', 'start_date', 'end_date', 'provider_images', 'machine_count')


class ImageSummarySerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Image
        view_name = 'api_v2:application-detail'
        fields = ('id', 'url', 'uuid', 'name', 'description', 'icon', 'start_date', 'end_date')


class ImageBookmarkSerializer(serializers.HyperlinkedModelSerializer):
    image = ImageSummarySerializer(source='application')
    user = UserSerializer()

    class Meta:
        model = ImageBookmark
        view_name = 'api_v2:applicationbookmark-detail'
        fields = ('id', 'url', 'image', 'user')
