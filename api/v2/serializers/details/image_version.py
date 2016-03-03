from core.models import ApplicationVersion as ImageVersion
from core.models import Application as Image
from core.models import License, BootScript
from core.models import ProviderMachine
from rest_framework import serializers
from api.v2.serializers.summaries import (
    BootScriptSummarySerializer,
    LicenseSummarySerializer,
    UserSummarySerializer,
    ImageSummarySerializer,
    IdentitySummarySerializer,
    ProviderMachineSummarySerializer,
    ImageVersionSummarySerializer)
from api.v2.serializers.fields import (
    ProviderMachineRelatedField, ModelRelatedField)
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
    min_mem = serializers.CharField(source='threshold.memory_min', read_only = True)
    min_cpu = serializers.CharField(source='threshold.cpu_min', read_only = True)
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
        if isinstance(user, AnonymousUser):
            filtered = obj.machines.filter(Q(instance_source__provider__public=True))
        else:
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
