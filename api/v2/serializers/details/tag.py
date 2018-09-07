from rest_framework import serializers

from api.v2.serializers.summaries import UserSummarySerializer
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField
from core.models import Tag


class TagSerializer(serializers.HyperlinkedModelSerializer):
    user = UserSummarySerializer(read_only=True)
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:tag-detail',
    )
    allow_access = serializers.SerializerMethodField()

    def _get_request_user(self):
        if 'request' not in self.context:
            raise ValueError("Expected 'request' context for this serializer")
        return self.context['request'].user

    def get_allow_access(self, tag):
        user = self._get_request_user()
        return tag.allow_access(user)

    class Meta:
        model = Tag
        fields = (
            'id', 'uuid', 'url', 'name',
            'description', 'user', 'allow_access')
