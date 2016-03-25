from core.models import ApplicationVersion as ImageVersion
from core.models import Application as Image
from core.models import (
    License, BootScript, ApplicationThreshold
)
from rest_framework import serializers
from api.v2.serializers.summaries import (
    BootScriptSummarySerializer,
    ImageSummarySerializer,
    ImageVersionSummarySerializer,
    IdentitySummarySerializer,
    LicenseSummarySerializer,
    ProviderMachineSummarySerializer,
    UserSummarySerializer
)
from api.v2.serializers.fields import ModelRelatedField
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField
from django.db.models import Q
from django.contrib.auth.models import AnonymousUser


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
    machines = serializers.SerializerMethodField('get_machines_for_user')
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

    def get_machines_for_user(self, obj):
        """
        Only show version as available on providers the user has access to
        """
        user = self.context['request'].user

        filtered = obj.machines
        if isinstance(user, AnonymousUser):
            filtered = obj.machines.filter(Q(instance_source__provider__public=True))
        elif not user.is_staff:
            filtered = obj.machines.filter(Q(instance_source__provider_id__in=user.provider_ids()))
        serializer = ProviderMachineSummarySerializer(
           filtered,
           context=self.context,
           many=True)
        return serializer.data

    class Meta:
        model = ImageVersion
        fields = ('id', 'url', 'parent', 'name', 'change_log',
                  'image', 'machines', 'allow_imaging',
                  'licenses', 'membership', 'min_mem', 'min_cpu', 'scripts',
                  'user', 'identity',
                  'start_date', 'end_date')

    def update(self, instance, validated_data):
        if 'min_cpu' in self.initial_data or 'min_mem' in self.initial_data:
            self.update_threshold(instance, validated_data)
        return super(ImageVersionSerializer, self).update(instance, validated_data)

    def validate_min_cpu(self, value):
        if value < 0 or value > 16:
            raise serializers.ValidationError(
                "Value of CPU must be between 1 & 16")
        return value

    def validate_min_mem(self, value):
        if value < 0 or value > 32 * 1024:
            raise serializers.ValidationError(
                "Value of mem must be between 1 & 32 GB")
        return value


    def update_threshold(self, instance, validated_data):
        current_threshold = instance.get_threshold()

        try:
            current_mem_min = current_threshold.memory_min
        except:
            current_mem_min = 0

        try:
            current_cpu_min = current_threshold.cpu_min
        except:
            current_cpu_min = 0

        try:
            new_mem_min = validated_data.get('threshold')['memory_min']
        except:
            new_mem_min = current_mem_min

        try:
            new_cpu_min = validated_data.get('threshold')['cpu_min']
        except:
            new_cpu_min = current_cpu_min

        if not current_threshold:
            new_threshold = ApplicationThreshold.objects.create(
                application_version=instance,
                memory_min=new_mem_min,
                cpu_min=new_cpu_min)
        else:
            new_threshold = ApplicationThreshold.objects.get(application_version=instance)
            new_threshold.memory_min = new_mem_min
            new_threshold.cpu_min = new_cpu_min
            new_threshold.save()

        validated_data['threshold'] = new_threshold
