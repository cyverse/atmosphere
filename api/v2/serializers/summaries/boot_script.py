from core.models import BootScript, ScriptType
from rest_framework import serializers


class BootScriptSummarySerializer(serializers.HyperlinkedModelSerializer):
    type = serializers.SlugRelatedField(
        source='script_type',
        slug_field='name',
        queryset=ScriptType.objects.all())

    class Meta:
        model = BootScript
        view_name = 'api:v2:license-detail'
        fields = ('id', 'title', 'type')
