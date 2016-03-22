from core.models.machine_request import MachineRequest
from core.models.user import AtmosphereUser
from core.models.instance import Instance
from core.models.instance_source import InstanceSource
from core.models.provider import Provider
from core.models.boot_script import BootScript
from core.models.license import License
from api.validators import no_special_characters
from rest_framework import serializers
from .new_threshold_field import NewThresholdField
from .boot_script_related_field import BootScriptRelatedField
from .license_related_field import LicenseRelatedField


class MachineRequestSerializer(serializers.ModelSerializer):

    """
    """
    instance = serializers.SlugRelatedField(
        slug_field='provider_alias',
        queryset=Instance.objects.all())
    status = serializers.CharField(default="pending", source='old_status')
    request_status = serializers.ReadOnlyField(source='get_request_status')
    parent_machine = serializers.ReadOnlyField(
        source="instance_source.identifier")

    sys = serializers.CharField(default="", source='system_files',
                                allow_blank=True,
                                required=False)
    software = serializers.CharField(default="No software listed",
                                     source='installed_software',
                                     allow_blank=True,
                                     required=False)
    exclude_files = serializers.CharField(default="", required=False)
    shared_with = serializers.CharField(source="access_list", required=False)

    name = serializers.CharField(source='new_application_name', validators=[no_special_characters])
    provider = serializers.SlugRelatedField(
        slug_field='uuid', source='new_machine_provider',
        queryset=Provider.objects.all()
    )
    owner = serializers.SlugRelatedField(slug_field='username',
                                         source='new_machine_owner',
                                         queryset=AtmosphereUser.objects.all()
                                         )
    vis = serializers.CharField(source='new_application_visibility')
    version_name = serializers.CharField(source='new_version_name',
            default="1.0", required=False)
    version_changes = serializers.CharField(source='new_version_change_log',
            default="1.0 - New Version Created", required=False)
    fork = serializers.BooleanField(source='new_version_forked',
                                    required=False)
    description = serializers.CharField(source='new_application_description',
                                        allow_blank=True,
                                        required=False)
    tags = serializers.CharField(source='new_version_tags', required=False,
                                 allow_blank=True)
    threshold = NewThresholdField(
        source='new_version_threshold',
        required=False)
    # TODO: Convert to 'LicenseField' and allow POST of ID instead of
    #      full-object. for additional support for the image creator
    scripts = BootScriptRelatedField(
        source='new_version_scripts',
        many=True, queryset=BootScript.objects.none(),
        required=False)
    licenses = LicenseRelatedField(
        source='new_version_licenses',
        many=True, queryset=License.objects.none(),
        required=False)
    new_machine = serializers.SlugRelatedField(
        slug_field='identifier', required=False,
        queryset=InstanceSource.objects.all()
    )

    class Meta:
        model = MachineRequest
        fields = ('id', 'instance', 'status', 'request_status', 'name', 'owner', 'provider',
                  'vis', 'description', 'tags', 'sys', 'software',
                  'threshold', 'fork', 'version_name', 'version_changes',
                  'exclude_files', 'shared_with', 'scripts', 'licenses',
                  'parent_machine', 'new_machine')
