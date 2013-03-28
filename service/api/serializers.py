from core.models.credential import Credential
from core.models.identity import Identity
from core.models.instance import Instance
from core.models.machine import ProviderMachine
from core.models.machine_request import MachineRequest, MachineExport
from core.models.profile import UserProfile
from core.models.provider import ProviderType, Provider
from core.models.size import Size
from core.models.tag import Tag
from core.models.volume import Volume
from core.models.group import Group

from rest_framework import serializers


class CredentialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Credential
        exclude = ('identity',)


class IdentitySerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source='creator_name')
    credentials = serializers.Field(source='credential_list')
    quota = serializers.Field(source='get_quota_dict')
    #URLs
    #instances = serializers.HyperlinkedIdentityField(
    #    view_name='instance-list', format='html')
    #volumes = serializers.HyperlinkedIdentityField(
    #    view_name='volume-list', format='html')
    #machines = serializers.HyperlinkedIdentityField(
    #    view_name='machine-list', format='html')

    class Meta:
        model = Identity
        fields = ('id', 'created_by', 'provider', 'credentials', 'quota')


class InstanceSerializer(serializers.ModelSerializer):
    #R/O Fields first!
    alias = serializers.CharField(read_only=True, source='provider_alias')
    alias_hash = serializers.CharField(read_only=True, source='hash_alias')
    created_by = serializers.CharField(read_only=True, source='creator_name')
    status = serializers.CharField(read_only=True, source='esh_status')
    size_alias = serializers.CharField(read_only=True, source='esh_size')
    machine_alias = serializers.CharField(read_only=True, source='esh_machine')
    machine_name = serializers.CharField(read_only=True,
                                         source='esh_machine_name')
    machine_alias_hash = serializers.CharField(read_only=True,
                                               source='hash_machine_alias')
    ip_address = serializers.CharField(read_only=True)
    start_date = serializers.DateTimeField(read_only=True)
    token = serializers.CharField(read_only=True)
    #Writeable fields
    name = serializers.CharField(source='name')
    tags = serializers.ManySlugRelatedField(slug_field='name',
                                            source='tags', read_only=False)

    class Meta:
        model = Instance
        exclude = ('id', 'end_date', 'provider_machine', 'provider_alias')


class MachineExportSerializer(serializers.ModelSerializer):
    """
    """
    instance = serializers.SlugRelatedField(slug_field='provider_alias')
    status = serializers.CharField(default="pending")

    owner = serializers.SlugRelatedField(slug_field='username',
                                         source='export_owner')
    export_file = serializers.CharField(read_only=True)

    class Meta:
        model = MachineExport


class MachineRequestSerializer(serializers.ModelSerializer):
    """
    """
    instance = serializers.SlugRelatedField(slug_field='provider_alias')
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
    provider = serializers.PrimaryKeyRelatedField(
        source='new_machine_provider')
    owner = serializers.SlugRelatedField(slug_field='username',
                                         source='new_machine_owner')
    vis = serializers.CharField(source='new_machine_visibility')
    description = serializers.CharField(source='new_machine_description',
                                        required=False)
    tags = serializers.CharField(source='new_machine_tags', required=False)

    new_machine = serializers.RelatedField(read_only=True)

    class Meta:
        model = MachineRequest
        fields = ('id', 'instance', 'status', 'name', 'owner', 'provider',
                  'vis', 'description', 'tags', 'sys', 'software',
                  'shared_with')


class IdentityRelatedField(serializers.RelatedField):

    def to_native(self, identity):
        quota_dict = identity.get_quota_dict()
        return {
            "id": identity.id,
            "provider_id": identity.provider.id,
            "quota": quota_dict,
        }

    def field_from_native(self, data, files, field_name, into):
        value = data.get(field_name)
        if value is None:
            return
        try:
            into[field_name] = Identity.objects.get(id=value)
        except Identity.DoesNotExist:
            into[field_name] = None


class ProfileSerializer(serializers.ModelSerializer):
    """
    """
    #TODO:Need to validate provider/identityy membership on id change
    username = serializers.CharField(read_only=True, source='user.username')
    groups = serializers.CharField(read_only=True, source='user.groups.all')
    selected_identity = IdentityRelatedField()

    class Meta:
        model = UserProfile
        exclude = ('id',)


class ProviderMachineSerializer(serializers.ModelSerializer):
    #R/O Fields first!
    alias = serializers.CharField(read_only=True, source='identifier')
    alias_hash = serializers.CharField(read_only=True, source='hash_alias')
    created_by = serializers.CharField(read_only=True,
                                       source='machine.created_by.username')
    icon = serializers.CharField(read_only=True, source='icon_url')
    private = serializers.CharField(read_only=True, source='machine.private')
    architecture = serializers.CharField(read_only=True,
                                         source='esh_architecture')
    ownerid = serializers.CharField(read_only=True, source='esh_ownerid')
    state = serializers.CharField(read_only=True, source='esh_state')
    #Writeable fields
    name = serializers.CharField(source='machine.name')
    tags = serializers.CharField(source='machine.tags.all')
    description = serializers.CharField(source='machine.description')
    start_date = serializers.CharField(source='machine.start_date')
    featured = serializers.BooleanField(source='machine.featured')

    class Meta:
        model = ProviderMachine
        exclude = ('id', 'provider', 'machine', 'identity')


class ProviderSerializer(serializers.ModelSerializer):
    type = serializers.SlugRelatedField(slug_field='name')

    class Meta:
        model = Provider
        exclude = ('active', 'start_date', 'end_date')


class GroupSerializer(serializers.ModelSerializer):
    identities = serializers.SerializerMethodField('get_identities')

    class Meta:
        model = Group
        exclude = ('id', 'providers')

    def get_identities(self, group):
        identities = group.identities.all()
        return map(lambda i:
                   {"id": i.id, "provider_id": i.provider_id},
                   identities)


class VolumeSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True, source='esh_status')
    attach_data = serializers.Field(source='esh_attach_data')

    class Meta:
        model = Volume
        exclude = ('id', 'end_date')


class ProviderSizeSerializer(serializers.ModelSerializer):
    occupancy = serializers.CharField(read_only=True, source='esh_occupancy')
    total = serializers.CharField(read_only=True, source='esh_total')
    remaining = serializers.CharField(read_only=True, source='esh_remaining')

    class Meta:
        model = Size
        exclude = ('id', 'start_date', 'end_date')


class ProviderTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderType


class TagSerializer(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(slug_field='username')
    description = serializers.CharField(blank=True)

    class Meta:
        model = Tag
