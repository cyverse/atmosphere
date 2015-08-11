from rest_framework import serializers
from core.models import BootScript
from .boot_script_serializer import BootScriptSerializer


class BootScriptRelatedField(serializers.PrimaryKeyRelatedField):

    def get_queryset(self):
        return BootScript.objects.all()

    def to_representation(self, value):
        script = BootScript.objects.get(pk=value.pk)
        serializer = BootScriptSerializer(script, context=self.context)
        return serializer.data

