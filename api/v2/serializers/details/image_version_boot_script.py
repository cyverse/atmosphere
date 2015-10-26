from rest_framework import serializers

from core.models import ApplicationVersionBootScript as ImageVersionBootScript
from core.models import ApplicationVersion as ImageVersion
from core.models import BootScript

from api.v2.serializers.summaries import (
    ImageVersionSummarySerializer, BootScriptSummarySerializer)


class ImageVersionRelatedField(serializers.PrimaryKeyRelatedField):

    def get_queryset(self):
        return ImageVersion.objects.all()

    def to_representation(self, value):
        image_version = ImageVersion.objects.get(pk=value.pk)
        serializer = ImageVersionSummarySerializer(
            image_version,
            context=self.context)
        return serializer.data


class BootScriptRelatedField(serializers.PrimaryKeyRelatedField):

    def get_queryset(self):
        return BootScript.objects.all()

    def to_representation(self, value):
        script = BootScript.objects.get(pk=value.pk)
        serializer = BootScriptSummarySerializer(script, context=self.context)
        return serializer.data


class ImageVersionBootScriptSerializer(serializers.HyperlinkedModelSerializer):
    image_version = ImageVersionRelatedField(
        queryset=ImageVersion.objects.none(), source='applicationversion')
    boot_script = BootScriptRelatedField(
        queryset=BootScript.objects.none(), source='bootscript')
    url = serializers.HyperlinkedIdentityField(
        view_name='api:v2:imageversion_bootscript-detail',
    )

    class Meta:
        model = ImageVersionBootScript
        fields = (
            'id',
            'url',
            'image_version',
            'boot_script'
        )
