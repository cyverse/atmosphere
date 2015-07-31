from core.models import BootScript, ScriptType
from rest_framework import serializers


class BootScriptSerializer(serializers.HyperlinkedModelSerializer):
    text = serializers.CharField(source='script_text')
    type = serializers.SlugRelatedField(
        source='script_type',
        slug_field='name',
        queryset=ScriptType.objects.all())

    def create(self, validated_data):

        if 'created_by' not in validated_data:
            request = self.context.get('request')
            if request and request.user:
                validated_data['created_by'] = request.user
        return super(BootScriptSerializer, self).create(validated_data)

    class Meta:
        model = BootScript
        view_name = 'api:v2:boot_script-detail'
        fields = ('id', 'title', 'text', 'type')
