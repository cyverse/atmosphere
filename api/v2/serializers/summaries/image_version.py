from core.models import ApplicationVersion as ImageVersion
from rest_framework import serializers

class ImageVersionSummarySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ImageVersion
        view_name = 'api:v2:imageversion-detail'
        fields = ('id', 'url', 'name',)
