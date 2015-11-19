from core.models import ApplicationBookmark as ImageBookmark, Application as Image
from rest_framework import serializers
from api.v2.serializers.summaries import UserSummarySerializer, ImageSummarySerializer
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class ImagePrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):

    def use_pk_only_optimization(self):
        return False

    def to_representation(self, value):
        serializer = ImageSummarySerializer(value, context=self.context)
        return serializer.data


class ImageBookmarkSerializer(serializers.HyperlinkedModelSerializer):
    image = ImagePrimaryKeyRelatedField(
        source='application',
        queryset=Image.objects.all())
    user = UserSummarySerializer(read_only=True)
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:applicationbookmark-detail',
    )
    def validate_image(self, value):
        """
        Check that the image has not already been bookmarked
        """
        user = self.context['request'].user

        try:
            existing_image_bookmark = ImageBookmark.objects.get(
                application=value,
                user=user)
            raise serializers.ValidationError("Image already bookmarked")
        except ImageBookmark.DoesNotExist:
            return value

    class Meta:
        model = ImageBookmark
        fields = ('id', 'uuid', 'url', 'image', 'user')
