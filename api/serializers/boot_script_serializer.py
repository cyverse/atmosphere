from core.models.post_boot import BootScript
from rest_framework import serializers


class BootScriptSerializer(serializers.ModelSerializer):
    created_by = serializers.SlugRelatedField(slug_field='username')
    script_type = serializers.SlugRelatedField(slug_field='name')
    class Meta:
        model = BootScript
        exclude = ('instances', 'applications',)