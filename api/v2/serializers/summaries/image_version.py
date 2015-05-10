from core.models import Application as Image
from rest_framework import serializers

class ImageVersionSummarySerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.CharField(read_only=True) # Required when its a uuid -- otherwise LONGINT
    icon = serializers.CharField(source='icon_url', read_only=True)
    membership = serializers.SlugRelatedField(slug_field='name', read_only=True, many=True) #NEW

    class Meta:
        model = Image
        view_name = 'api_v2:imageversion-detail'
        fields = ('id', 'url', 'name', 'description', 'icon', 'start_date', 'end_date','membership')
