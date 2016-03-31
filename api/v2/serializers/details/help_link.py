from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from core.models.template import HelpLink


class HelpLinkSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        raise ValidationError("Cannot create new help links via API")

    class Meta:
        model = HelpLink
        fields = (
            'link_key',
            'topic',
            'context',
            'href'
        )
