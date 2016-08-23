from rest_framework import exceptions, serializers

from core.models import (
    ApplicationVersion, ProviderMachine, Group,
    BootScript, Provider, License, Instance,
    MachineRequest, Identity,
    AtmosphereUser as User,
    IdentityMembership
)
from core.models.status_type import StatusType

from api.v2.serializers.summaries import (
    AllocationSummarySerializer,
    ImageVersionSummarySerializer,
    BootScriptSummarySerializer,
    IdentitySummarySerializer,
    GroupSummarySerializer,
    InstanceSummarySerializer,
    LicenseSummarySerializer,
    UserSummarySerializer,
    ProviderSummarySerializer,
    ProviderMachineSummarySerializer,
    QuotaSummarySerializer,
    UserSummarySerializer,
    StatusTypeSummarySerializer
)
from api.v2.serializers.fields import (
    ProviderMachineRelatedField, ModelRelatedField)
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField
from api.validators import NoSpecialCharacters

class UserRelatedField(serializers.PrimaryKeyRelatedField):

    def get_queryset(self):
        return User.objects.all()

    def to_representation(self, value):
        user = User.objects.get(pk=value.pk)
        serializer = UserSummarySerializer(user, context=self.context)
        return serializer.data

class InstanceRelatedField(serializers.RelatedField):
    
    def get_queryset(self):
        return Instance.objects.all()

    def to_representation(self, value):
        instance = Instance.objects.get(pk=value.pk)
        serializer = InstanceSummarySerializer(instance, context=self.context)
        return serializer.data


class ProviderRelatedField(serializers.RelatedField):

    def get_queryset(self):
        return Provider.objects.all()
    
    def to_representation(self, value):
        provider = Provider.objects.get(id=value.id)
        serializer = ProviderSummarySerializer(provider, context=self.context)
        return serializer.data


class IdentityRelatedField(serializers.RelatedField):

    def get_queryset(self):
        return Identity.objects.all()

    def to_representation(self, value):
        identity = Identity.objects.get(pk=value.pk)
        serializer = IdentitySummarySerializer(identity, context=self.context)
        return serializer.data

    def to_internal_value(self, data):
        queryset = self.get_queryset()
        if isinstance(data, dict):
            identity = data.get("id", None)
        else:
            identity = data
        try:
            return queryset.get(id=identity)
        except:
            raise exceptions.ValidationError(
                "Identity with id '%s' does not exist."
                % identity
            )


class StatusTypeRelatedField(serializers.RelatedField):

    def get_queryset(self):
        return StatusType.objects.all()

    def to_representation(self, value):
        status_type = StatusType.objects.get(pk=value.pk)
        serializer = StatusTypeSummarySerializer(
            status_type,
            context=self.context)
        return serializer.data

    def to_internal_value(self, data):
        queryset = self.get_queryset()
        if isinstance(data, dict):
            identity = data.get("id", None)
        else:
            identity = data

        try:
            return queryset.get(id=identity)
        except:
            raise exceptions.ValidationError(
                "StatusType with id '%s' does not exist."
                % identity
            )


class MachineRequestSerializer(serializers.HyperlinkedModelSerializer):

    uuid = serializers.CharField(read_only=True)
    identity = IdentityRelatedField(source='membership.identity',
                                    queryset=Identity.objects.none())
    # This is a *STAFF EXCLUSIVE* serializer. These are the values that make it that way:
    admin_message = serializers.CharField(read_only=True)
    parent_machine = ModelRelatedField(
       required=False,
       lookup_field="uuid",
       queryset=ProviderMachine.objects.all(),
       serializer_class=ProviderMachineSummarySerializer,
       style={'base_template': 'input.html'})

    instance = ModelRelatedField(
        queryset=Instance.objects.all(),
        serializer_class=InstanceSummarySerializer,
        style={'base_template': 'input.html'})
    status = StatusTypeRelatedField(queryset=StatusType.objects.none(),
                                    allow_null=True,
                                    required=False)
    old_status = serializers.CharField(required = False)

    new_application_visibility = serializers.CharField()
    new_application_version = ImageVersionSummarySerializer(read_only=True)
    new_application_name = serializers.CharField(validators=[NoSpecialCharacters('!"#$%&\'*+,/;<=>?@[\\]^_`{|}~')])
    new_application_description = serializers.CharField()
    access_list = serializers.CharField(allow_blank=True)
    system_files = serializers.CharField(allow_blank=True, required=False)
    installed_software = serializers.CharField()
    exclude_files = serializers.CharField(allow_blank=True)
    new_version_name = serializers.CharField()
    new_version_change_log = serializers.CharField(required=False, allow_blank=True)
    new_version_tags = serializers.CharField(required=False, allow_blank=True)
    new_version_memory_min = serializers.CharField()
    new_version_cpu_min = serializers.CharField()
    new_version_allow_imaging = serializers.BooleanField()
    new_version_forked = serializers.BooleanField()
    new_version_licenses = ModelRelatedField(
        many=True,
        queryset=License.objects.all(),
        serializer_class=LicenseSummarySerializer,
        style={'base_template': 'input.html'},
        required=False)
    new_version_scripts = ModelRelatedField(
        many=True,
        queryset=BootScript.objects.all(),
        serializer_class=BootScriptSummarySerializer,
        style={'base_template': 'input.html'},
        required=False)
    new_version_membership = ModelRelatedField(
        many=True,
        queryset=Group.objects.all(),
        serializer_class=GroupSummarySerializer,
        style={'base_template':'input.html'},
        required=False)
    new_machine_provider = ModelRelatedField(
        queryset=Provider.objects.all(),
        serializer_class=ProviderSummarySerializer,
        style={'base_template':'input.html'})
    new_machine_owner = ModelRelatedField(
        queryset=User.objects.all(),
        serializer_class = UserSummarySerializer,
        style={'base_template':'input.html'})
    start_date = serializers.DateTimeField(read_only=True)
    end_date = serializers.DateTimeField(read_only=True)
    new_machine = ModelRelatedField(
        required = False,
        queryset = ProviderMachine.objects.all(),
        serializer_class = ProviderMachineSummarySerializer,
        style = {'base_template':'input.html'})
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:machinerequest-detail',
    )

    class Meta:
        model = MachineRequest
        fields = (
            'id',
            'uuid',
            'url',
            'instance',
            'identity',
            'status',
            'old_status',
            'parent_machine',
            'admin_message',
            'new_application_name',
            'new_application_description',
            'new_application_visibility',
            'access_list',
            'system_files',
            'installed_software',
            'exclude_files',
            'new_version_name',
            'new_version_change_log',
            'new_version_tags',
            'new_version_memory_min',
            'new_version_cpu_min',
            'new_version_allow_imaging',
            'new_version_forked',
            'new_version_licenses',
            'new_version_scripts',
            'new_version_membership',
            'new_machine_provider',
            'new_machine_owner',
            'start_date',
            'end_date',
            'new_machine',
            'new_application_version'
        )


class UserMachineRequestSerializer(serializers.HyperlinkedModelSerializer):

    uuid = serializers.CharField(read_only=True)
    admin_message = serializers.CharField(read_only=True)
    instance = ModelRelatedField(
        queryset=Instance.objects.all(),
        serializer_class=InstanceSummarySerializer,
        style={'base_template': 'input.html'})
    status = StatusTypeRelatedField(queryset=StatusType.objects.none(),
                                    allow_null=True,
                                    required=False)
    old_status = serializers.CharField(required = False)

    new_application_visibility = serializers.CharField()
    new_application_version = ImageVersionSummarySerializer(read_only=True)
    new_application_name = serializers.CharField(validators=[NoSpecialCharacters('!"#$%&\'*+,/;<=>?@[\\]^`{|}~')])
    new_application_description = serializers.CharField()
    access_list = serializers.CharField(allow_blank=True)
    system_files = serializers.CharField(allow_blank=True, required=False)
    installed_software = serializers.CharField()
    exclude_files = serializers.CharField(allow_blank=True)
    new_version_name = serializers.CharField()
    new_version_change_log = serializers.CharField(required=False, allow_blank=True)
    new_version_tags = serializers.CharField(required=False, allow_blank=True)
    new_version_memory_min = serializers.CharField()
    new_version_cpu_min = serializers.CharField()
    new_version_allow_imaging = serializers.BooleanField()
    new_version_forked = serializers.BooleanField()
    new_version_licenses = ModelRelatedField(
        many=True,
        queryset=License.objects.all(),
        serializer_class=LicenseSummarySerializer,
        style={'base_template': 'input.html'},
        required=False)
    new_version_scripts = ModelRelatedField(
        many=True,
        queryset=BootScript.objects.all(),
        serializer_class=BootScriptSummarySerializer,
        style={'base_template': 'input.html'},
        required=False)
    new_version_membership = ModelRelatedField(
        many=True,
        queryset=Group.objects.all(),
        serializer_class=GroupSummarySerializer,
        style={'base_template':'input.html'},
        required=False)
    new_machine_provider = ModelRelatedField(
        queryset=Provider.objects.all(),
        serializer_class=ProviderSummarySerializer,
        style={'base_template':'input.html'},
        required=False)
    # Absent: new_machine_owner -- determined by User submission
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:machinerequest-detail',
    )
    #FIXME: tags are missing here.
    # version change log is missing
    # 
    class Meta:
        model = MachineRequest
        fields = (
            'id',
            'uuid',
            'url',
            'admin_message',
            'instance',
            'status',
            'old_status',
            'new_application_visibility',
            'new_application_version',
            'new_application_name',
            'new_application_description',
            'access_list',
            'system_files',
            'installed_software',
            'exclude_files',
            'new_version_name',
            'new_version_change_log',
            'new_version_tags',
            'new_version_memory_min',
            'new_version_cpu_min',
            'new_version_allow_imaging',
            'new_version_forked',
            'new_version_licenses',
            'new_version_scripts',
            'new_version_membership',
            'new_machine_provider',
        )
