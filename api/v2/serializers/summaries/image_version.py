from core.models import ApplicationVersion as ImageVersion
from rest_framework import serializers

class ImageVersionSummarySerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.CharField(read_only=True) # Required when its a uuid -- otherwise LONGINT
    icon = serializers.CharField(source='icon_url', read_only=True)
    membership = serializers.SlugRelatedField(slug_field='name', read_only=True, many=True) #NEW-Bad form?

    class Meta:
        model = ImageVersion
        view_name = 'api_v2:imageversion-detail'
        fields = ('id', 'url', 'name', 'description', 'icon', 'allow_imaging', 'membership', 'start_date', 'end_date')
