import django_filters

from rest_framework import serializers

from core.models.boot_script import BootScript, ScriptType
from core.models.user import AtmosphereUser
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class StrategyCharField(serializers.CharField):
    """
    This CharField converts 'string' API representations to boolean model representation
    """

    def to_internal_value(self, data):
        """
        For now, only two strategies, controlled by boolean.
        This may change as we expand..
        """
        data = data.lower()
        if data == 'once':
            return False
        elif data == 'always':
            return True
        raise serializers.ValidationError(
            "Unexpected strategy value (%s) Expected: ['once', 'always']" % data)

    def to_representation(self, value):
        as_string = "once"
        if value == True:
            as_string = "always"
        return super(StrategyCharField, self).to_representation(as_string)

class BootScriptSerializer(serializers.HyperlinkedModelSerializer):
    created_by = serializers.SlugRelatedField(
        slug_field='username', queryset=AtmosphereUser.objects.all(),
    )
    text = serializers.CharField(source='script_text')
    strategy = StrategyCharField(source='run_every_deploy')
    type = serializers.SlugRelatedField(
        source='script_type',
        slug_field='name',
        queryset=ScriptType.objects.all())
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:bootscript-detail',
    )

    def is_valid(self, raise_exception=False):
        """
        """
        raw_type = self.initial_data.get("type", "")
        if raw_type:
            raw_type = raw_type.lower()
        if 'raw text' in raw_type:
            ScriptType.objects.get_or_create(name="Raw Text")
        elif 'url' in raw_type:
            ScriptType.objects.get_or_create(name="URL")

        if 'created_by' not in self.initial_data:
            request = self.context.get('request')
            if request and request.user:
                self.initial_data['created_by'] = request.user
        return super(BootScriptSerializer, self).is_valid(
                raise_exception=raise_exception)

    class Meta:
        model = BootScript
        fields = ('id', 'url', 'uuid', 'created_by', 'title', 'text', 'type', 'strategy')
