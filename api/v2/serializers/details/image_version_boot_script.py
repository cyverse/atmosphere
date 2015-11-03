from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator 
from core.models import ApplicationVersionBootScript as ImageVersionBootScript
from core.models import ApplicationVersion as ImageVersion
from core.models import BootScript

from api.v2.serializers.summaries import (
    ImageVersionSummarySerializer, BootScriptSummarySerializer)
from api.v2.serializers.fields.base import ModelRelatedField


class ImageVersionBootScriptSerializer(serializers.HyperlinkedModelSerializer):
    image_version = ModelRelatedField(
        queryset=ImageVersion.objects.all(),
        serializer_class=ImageVersionSummarySerializer,
        style={'base_template': 'input.html'},
        required=False)
    boot_script = ModelRelatedField(
        queryset=BootScript.objects.all(),
        serializer_class=BootScriptSummarySerializer,
        style={'base_template': 'input.html'},
        lookup_field='uuid',
        required=False)
    url = serializers.HyperlinkedIdentityField(
        view_name='api:v2:imageversion_bootscript-detail',
    )

    class Meta:
        model = ImageVersionBootScript
        validators = [
            UniqueTogetherValidator(
                queryset=ImageVersionBootScript.objects.all(),
                fields=('image_version', 'boot_script')
            )
        ]
        fields = (
            'id',
            'url',
            'image_version',
            'boot_script'
        )
