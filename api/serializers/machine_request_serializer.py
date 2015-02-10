from core.models.machine_request import MachineRequest
from core.models.user import AtmosphereUser
from core.models.instance import Instance
from core.models.provider import Provider
from core.models.machine import ProviderMachine
from rest_framework import serializers
from .new_threshold_field import NewThresholdField
from .license_serializer import LicenseSerializer


class MachineRequestSerializer(serializers.ModelSerializer):
    """
    """
    instance = serializers.SlugRelatedField(slug_field='provider_alias', queryset=Instance.objects.all())
    status = serializers.CharField(default="pending")
    parent_machine = serializers.SlugRelatedField(slug_field='identifier',
                                                  read_only=True)

    sys = serializers.CharField(default="", source='iplant_sys_files',
                                required=False)
    software = serializers.CharField(default="No software listed",
                                     source='installed_software',
                                     required=False)
    exclude_files = serializers.CharField(default="", required=False)
    shared_with = serializers.CharField(source="access_list", required=False)

    name = serializers.CharField(source='new_machine_name')
    provider = serializers.SlugRelatedField(
        slug_field='uuid', source='new_machine_provider',
        queryset=Provider.objects.all()
    )
    owner = serializers.SlugRelatedField(slug_field='username',
                                         source='new_machine_owner',
                                         queryset=AtmosphereUser.objects.all()
    )
    vis = serializers.CharField(source='new_machine_visibility')
    version = serializers.CharField(source='new_machine_version',
        required=False)
    fork = serializers.BooleanField(source='new_machine_forked',
        required=False)
    description = serializers.CharField(source='new_machine_description',
                                        required=False)
    tags = serializers.CharField(source='new_machine_tags', required=False)
    threshold = NewThresholdField(source='new_machine_threshold')
    #TODO: Convert to 'LicenseField' and allow POST of ID instead of
    #      full-object. for additional support for the image creator
    licenses = LicenseSerializer(source='new_machine_licenses.all', many=True)
    new_machine = serializers.SlugRelatedField(slug_field='identifier',
                                               required=False,
                                               queryset=ProviderMachine.objects.all()
    )

    class Meta:
        model = MachineRequest
        fields = ('id', 'instance', 'status', 'name', 'owner', 'provider',
                  'vis', 'description', 'tags', 'sys', 'software',
                  'threshold', 'fork', 'version', 'parent_machine',
                  'exclude_files', 'shared_with', 'licenses', 'new_machine')
