from core.models.boot_script import BootScript, ScriptType
from core.models.user import AtmosphereUser
from rest_framework import serializers


class BootScriptSerializer(serializers.ModelSerializer):
    created_by = serializers.SlugRelatedField(
        slug_field='username',
        queryset=AtmosphereUser.objects.all())
    script_type = serializers.SlugRelatedField(
        slug_field='name',
        queryset=ScriptType.objects.all())

    class Meta:
        model = BootScript
        exclude = ('instances', 'applications',)
