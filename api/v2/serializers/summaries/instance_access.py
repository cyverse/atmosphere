from rest_framework import serializers

from core.models import InstanceAccess


class InstanceAccessSummarySerializer(serializers.HyperlinkedModelSerializer):
    user = serializers.SlugRelatedField(slug_field='username', read_only=True)
    status = serializers.SlugRelatedField(slug_field='name', read_only=True)
    url = serializers.HyperlinkedIdentityField(view_name='api:v2:instanceaccess-detail')

    class Meta:
        model = InstanceAccess
        fields = ('id', 'url', 'status', 'user')
