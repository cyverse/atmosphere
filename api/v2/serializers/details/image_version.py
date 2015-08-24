from core.models import ApplicationVersion as ImageVersion
from core.models import Application as Image
from core.models import License, BootScript
from rest_framework import serializers
from api.v2.serializers.summaries import (
    BootScriptSummarySerializer,
    LicenseSummarySerializer,
    UserSummarySerializer,
    ImageSummarySerializer,
    IdentitySummarySerializer,
    ImageVersionSummarySerializer)
from api.v2.serializers.fields import (
    ProviderMachineRelatedField, ModelRelatedField)


class ImageVersionSerializer(serializers.HyperlinkedModelSerializer):

    """
    Serializer for ApplicationVersion (aka 'image_version')
    """
    # NOTE: Implicitly included via 'fields'
    # id, application
    parent = ImageVersionSummarySerializer()
    # name, change_log, allow_imaging
    licenses = ModelRelatedField(
        many=True, queryset=License.objects.all(),
        serializer_class=LicenseSummarySerializer,
        style={'base_template': 'input.html'})
    scripts = ModelRelatedField(
        source='boot_scripts', many=True,
        queryset=BootScript.objects.all(),
        serializer_class=BootScriptSummarySerializer,
        style={'base_template': 'input.html'})
    membership = serializers.SlugRelatedField(
        slug_field='name',
        read_only=True,
        many=True)  # NEW
    user = UserSummarySerializer(source='created_by')
    identity = IdentitySummarySerializer(source='created_by_identity')
    machines = ProviderMachineRelatedField(many=True)
    image = ModelRelatedField(
        source='application',
        queryset=Image.objects.all(),
        serializer_class=ImageSummarySerializer,
        style={'base_template': 'input.html'})
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField(allow_null=True)

    class Meta:
        model = ImageVersion
        view_name = 'api:v2:providermachine-detail'
        fields = ('id', 'parent', 'name', 'change_log',
                  'image', 'machines', 'allow_imaging',
                  'licenses', 'membership', 'scripts',
                  'user', 'identity',
                  'start_date', 'end_date')
