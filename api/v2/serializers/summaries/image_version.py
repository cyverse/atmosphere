from core.models import ApplicationVersion as ImageVersion
from rest_framework import serializers

class ImageVersionSummarySerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.CharField(read_only=True) # Required when its a uuid -- otherwise LONGINT
    membership = serializers.SlugRelatedField(slug_field='name', read_only=True, many=True) #NEW-Bad form?

    class Meta:
        model = ImageVersion
        view_name = 'api:v2:imageversion-detail'
        fields = ('id', 'url', 'name','membership')
