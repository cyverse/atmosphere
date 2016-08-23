from rest_framework import serializers

from atmosphere.settings import BLACKLIST_TAGS

from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField
from core.models import Tag


class TagSummarySerializer(serializers.HyperlinkedModelSerializer):
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:tag-detail',
    )
    allow_access = serializers.SerializerMethodField()

    def _get_request_user(self):
        if 'request' not in self.context:
            raise ValueError("Expected 'request' context for this serializer")
        return self.context['request'].user

    def get_allow_access(self, tag):
        tag_name = tag.name.lower()
        user = self._get_request_user()
        if user and (user.is_staff or user.is_superuser):
            return True
        in_black_list = any(tag_name == black_tag.lower()
                            for black_tag in BLACKLIST_TAGS)
        return not in_black_list

    class Meta:
        model = Tag
        fields = ('id', 'uuid', 'url', 'name', 'description', 'allow_access')
