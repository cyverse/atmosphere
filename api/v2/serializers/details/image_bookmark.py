from core.models import ApplicationBookmark as ImageBookmark, Application as Image
from rest_framework import serializers
from ..summaries import UserSummarySerializer, ImageSummarySerializer


class ImagePrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):

    def use_pk_only_optimization(self):
        return False

    def to_representation(self, value):
        serializer = ImageSummarySerializer(value, context=self.context)
        return serializer.data


class ImageBookmarkSerializer(serializers.HyperlinkedModelSerializer):
    image = ImagePrimaryKeyRelatedField(source='application', queryset=Image.objects.all())
    user = UserSummarySerializer(read_only=True)

    class Meta:
        model = ImageBookmark
        view_name = 'api_v2:applicationbookmark-detail'
        fields = ('id', 'url', 'image', 'user')
