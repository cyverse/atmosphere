from core.models import BootScript, ScriptType
from rest_framework import serializers
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class BootScriptSummarySerializer(serializers.HyperlinkedModelSerializer):
    type = serializers.SlugRelatedField(
        source='script_type',
        slug_field='name',
        queryset=ScriptType.objects.all())
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:bootscript-detail',
    )
    class Meta:
        model = BootScript
        fields = ('id', 'url', 'uuid', 'title', 'type')
