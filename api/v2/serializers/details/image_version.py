from core.models import ApplicationVersion as ImageVersion
from core.models import Application as Image
from core.models import License, BootScript, ProviderMachine, ApplicationThreshold
from rest_framework import serializers
from api.v2.serializers.summaries import (
    BootScriptSummarySerializer,
    LicenseSummarySerializer,
    UserSummarySerializer,
    ImageSummarySerializer,
    IdentitySummarySerializer,
    ImageVersionSummarySerializer,
    ProviderMachineSummarySerializer)
from api.v2.serializers.fields import (
    ProviderMachineRelatedField, ModelRelatedField)
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


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
    machines = ModelRelatedField(many=True, queryset=ProviderMachine.objects.all(),
        serializer_class=ProviderMachineSummarySerializer,
        style={'base_template': 'input.html'})
    image = ModelRelatedField(
        source='application',
        queryset=Image.objects.all(),
        serializer_class=ImageSummarySerializer,
        style={'base_template': 'input.html'})
    start_date = serializers.DateTimeField()
    min_mem = serializers.IntegerField(source='threshold.memory_min')
    min_cpu = serializers.IntegerField(source='threshold.cpu_min')
    end_date = serializers.DateTimeField(allow_null=True)
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:imageversion-detail',
        uuid_field='id'
    )
    class Meta:
        model = ImageVersion
        fields = ('id', 'url', 'parent', 'name', 'change_log',
                  'image', 'machines', 'allow_imaging',
                  'licenses', 'membership', 'min_mem', 'min_cpu', 'scripts',
                  'user', 'identity',
                  'start_date', 'end_date')

    def update(self, instance, validated_data):
        current_threshold = instance.application.get_threshold()
        current_mem_min = current_threshold.memory_min
        current_cpu_min = current_threshold.cpu_min

        try:
            new_mem_min = validated_data.get('threshold')['memory_min']
        except:
            new_mem_min = current_mem_min

        try:
            new_cpu_min = validated_data.get('threshold')['cpu_min']
        except:
            new_cpu_min = current_cpu_min

        # get item at 0 to retireve the item itself, we don't care if it was created
        new_threshold = ApplicationThreshold.objects.get_or_create(memory_min=new_mem_min, cpu_min=new_cpu_min)[0]
        instance.threshold = new_threshold
        instance.save()
        return instance
