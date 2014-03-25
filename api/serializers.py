from django.contrib.auth.models import AnonymousUser

from core.models.application import Application, ApplicationScore,\
        ApplicationBookmark
from core.models.credential import Credential
from core.models.group import IdentityMembership
from core.models.identity import Identity
from core.models.instance import Instance
from core.models.machine import ProviderMachine
from core.models.machine_request import MachineRequest
from core.models.machine_export import MachineExport
from core.models.maintenance import MaintenanceRecord
from core.models.profile import UserProfile
from core.models.provider import ProviderType, Provider
from core.models.size import Size
from core.models.step import Step
from core.models.tag import Tag, find_or_create_tag
from core.models.user import AtmosphereUser
from core.models.volume import Volume
from core.models.group import Group

from rest_framework import serializers

from rest_framework import pagination

from threepio import logger


class AccountSerializer(serializers.Serializer):
    pass
    #Define fields here
    #TODO: Define a spec that we expect from list_users across all providers

class ProviderSerializer(serializers.ModelSerializer):
    type = serializers.SlugRelatedField(slug_field='name')
    location = serializers.CharField(source='get_location')
    #membership = serializers.Field(source='get_membership')

    class Meta:
        model = Provider
        exclude = ('active', 'start_date', 'end_date')

class CleanedIdentitySerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source='creator_name')
    credentials = serializers.Field(source='get_credentials')
    quota = serializers.Field(source='get_quota_dict')
    membership = serializers.Field(source='get_membership')

    class Meta:
        model = Identity
        fields = ('id', 'created_by', 'provider', )


class IdentitySerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source='creator_name')
    credentials = serializers.Field(source='get_credentials')
    quota = serializers.Field(source='get_quota_dict')
    membership = serializers.Field(source='get_membership')

    class Meta:
        model = Identity
        fields = ('id', 'created_by', 'provider', 'credentials', 'quota',
                  'membership')

class AppBookmarkField(serializers.WritableField):

    def to_native(self, bookmark_mgr):
        request_user = self.root.request_user
        if type(request_user) == AnonymousUser:
            return False
        try:
            bookmark_mgr.get(user=request_user)
            return True
        except ApplicationBookmark.DoesNotExist:
            return False

    def field_from_native(self, data, files, field_name, into):
        value = data.get(field_name)
        if value is None:
            return
        app = self.root.object
        user = self.root.request_user
        if value:
            ApplicationBookmark.objects.\
                    get_or_create(application=app, user=user)
            result = True
        else:
            ApplicationBookmark.objects\
                    .filter(application=app, user=user).delete()
            result = False
        into[field_name] = result
    
class ApplicationSerializer(serializers.Serializer):
    #Read-Only Fields
    uuid = serializers.CharField(read_only=True)
    icon = serializers.CharField(read_only=True, source='icon_url')
    created_by = serializers.SlugRelatedField(slug_field='username',
                                              source='created_by',
                                              read_only=True)
    #scores = serializers.Field(source='get_scores')
    uuid_hash = serializers.CharField(read_only=True, source='hash_uuid')
    #Writeable Fields
    name = serializers.CharField(source='name')
    tags = serializers.CharField(source='tags.all')
    description = serializers.CharField(source='description')
    start_date = serializers.CharField(source='start_date')
    end_date = serializers.CharField(source='end_date',
                                     required=False, read_only=True)
    private = serializers.BooleanField(source='private')
    featured = serializers.BooleanField(source='featured')
    machines = serializers.RelatedField(source='get_provider_machines',
                                              read_only=True)
    is_bookmarked = AppBookmarkField(source="bookmarks.all")
    def __init__(self, *args, **kwargs):
        context = kwargs.get('context',{})
        user = context.get('user')
        request = context.get('request')
        if not user and not request:
            raise Exception("This Serializer REQUIRES the kwarg "
                            "context, with key 'request' or 'user'"
                            " for ex: context={'user':user}")
        if user:
            self.request_user = user
            #NOTE: Makes debugging easier.
            if type(self.request_user) == str:
                self.request_user = AtmosphereUser.objects.get(
                        username=self.request_user)
        else:
            self.request_user = request.user
        super(ApplicationSerializer, self).__init__(*args, **kwargs)

    class Meta:
        model = Application

class ApplicationScoreSerializer(serializers.ModelSerializer):
    """
    """
    #TODO:Need to validate provider/identity membership on id change
    username = serializers.CharField(read_only=True, source='user.username')
    application = serializers.CharField(read_only=True, source='application.name')
    vote = serializers.CharField(read_only=True, source='get_vote_name')

    class Meta:
        model = ApplicationScore
        fields = ('username',"application", "vote")


class ProjectSerializer(serializers.ModelSerializer):
    """
    NOTE: To properly use ProjectSerializer you SHOULD be passing the request!
    """
    name = serializers.SerializerMethodField('get_project_name')
    description = serializers.SerializerMethodField('get_project_description')
    instances = serializers.SerializerMethodField('get_project_instances')
    volumes = serializers.SerializerMethodField('get_project_volumes')
    applications = serializers.SerializerMethodField('get_project_applications')

    class Meta:
        model = AtmosphereUser
        fields = ('name','description', 'instances', 'volumes', 'applications')
    def get_request_user(self):
        request = self.context.get('request', None)
        if not request:
            return None
        user = request.user
        return user
    def get_project_name(self, user):
        return "default"
    def get_project_description(self, user):
        return "Blah"
    def get_project_instances(self, user):
        if not user:
            user = self.get_request_user()
        active_providers = Provider.get_active()
        core_instances = user.instance_set.filter(
                    end_date=None,
                    provider_machine__provider__in=active_providers)
        instances = InstanceSerializer(core_instances, many=True).data
        return instances
    def get_project_volumes(self, user):
        if not user:
            user = self.get_request_user()
        active_providers = Provider.get_active()
        core_volumes = user.volume_set.filter(end_date=None,
                    provider__in=active_providers)
        volumes = VolumeSerializer(core_volumes, many=True).data
        return volumes

    def get_project_applications(self, user):
        if not user:
            user = self.get_request_user()
        active_providers = Provider.get_active()
        core_applications = user.application_set.filter(end_date=None)
        applications = ApplicationSerializer(core_applications, many=True).data
        return applications

class CredentialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Credential
        exclude = ('identity',)


class TagRelatedField(serializers.SlugRelatedField):

    def to_native(self, tag):
        return super(TagRelatedField, self).to_native(tag)

    def field_from_native(self, data, files, field_name, into):
        value = data.get(field_name)
        if value is None:
            return
        try:
            tags = []
            for tagname in value:
                tag = find_or_create_tag(tagname, None)
                tags.append(tag)
            into[field_name] = tags
        except Identity.DoesNotExist:
            into[field_name] = None
        return


class InstanceSerializer(serializers.ModelSerializer):
    #R/O Fields first!
    alias = serializers.CharField(read_only=True, source='provider_alias')
    alias_hash = serializers.CharField(read_only=True, source='hash_alias')
    #created_by = serializers.CharField(read_only=True, source='creator_name')
    created_by = serializers.SlugRelatedField(slug_field='username',
                                              source='created_by',
                                              read_only=True)
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
    has_shell = serializers.BooleanField(read_only=True, source='shell')
    has_vnc = serializers.BooleanField(read_only=True, source='vnc')
    #provider = serializers.CharField(read_only=True, source='provider_name')
    identity = CleanedIdentitySerializer(source="created_by_identity")
    #Writeable fields
    name = serializers.CharField()
    tags = TagRelatedField(slug_field='name', source='tags', many=True)

    class Meta:
        model = Instance
        exclude = ('id', 'end_date', 'provider_machine', 'provider_alias',
                   'shell', 'vnc', 'password', 'created_by_identity')


class InstanceHistorySerializer(serializers.ModelSerializer):
    #R/O Fields first!
    alias = serializers.CharField(read_only=True, source='provider_alias')
    alias_hash = serializers.CharField(read_only=True, source='hash_alias')
    created_by = serializers.SlugRelatedField(slug_field='username',
                                              source='created_by',
                                              read_only=True)
    size_alias = serializers.CharField(read_only=True, source='esh_size')
    machine_alias = serializers.CharField(read_only=True, source='esh_machine')
    machine_name = serializers.CharField(read_only=True,
                                         source='esh_machine_name')
    machine_alias_hash = serializers.CharField(read_only=True,
                                               source='hash_machine_alias')
    ip_address = serializers.CharField(read_only=True)
    start_date = serializers.DateTimeField(read_only=True)
    end_date = serializers.DateTimeField(read_only=True)
    active_time = serializers.DateTimeField(read_only=True, source='get_active_time')
    provider = serializers.CharField(read_only=True, source='provider_name')
    #Writeable fields
    name = serializers.CharField()
    tags = TagRelatedField(slug_field='name', source='tags', many=True)

    class Meta:
        model = Instance
        exclude = ('id', 'provider_machine', 'provider_alias',
                   'shell', 'vnc', 'created_by_identity')


class PaginatedInstanceHistorySerializer(pagination.PaginationSerializer):
    """
    Serializes page objects of Instance querysets.
    """
    class Meta:
        object_serializer_class = InstanceHistorySerializer

class PaginatedInstanceSerializer(pagination.PaginationSerializer):
    """
    Serializes page objects of Instance querysets.
    """
    class Meta:
        object_serializer_class = InstanceSerializer


class MachineExportSerializer(serializers.ModelSerializer):
    """
    """
    name = serializers.CharField(source='export_name')
    instance = serializers.SlugRelatedField(slug_field='provider_alias')
    status = serializers.CharField(default="pending")
    disk_format = serializers.CharField(source='export_format')
    owner = serializers.SlugRelatedField(slug_field='username',
                                         source='export_owner')
    file = serializers.CharField(read_only=True, default="",
                                 required=False, source='export_file')

    class Meta:
        model = MachineExport
        fields = ('id', 'instance', 'status', 'name',
                  'owner', 'disk_format', 'file')


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
    new_machine = serializers.SlugRelatedField(slug_field='identifier',
            required=False)

    class Meta:
        model = MachineRequest
        fields = ('id', 'instance', 'status', 'name', 'owner', 'provider',
                  'vis', 'description', 'tags', 'sys', 'software',
                  'shared_with', 'new_machine')


class MaintenanceRecordSerializer(serializers.ModelSerializer):
    provider_id = serializers.Field(source='provider.id')

    class Meta:
        model = MaintenanceRecord
        exclude = ('provider',)


class IdentityDetailSerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source='creator_name')
    quota = serializers.Field(source='get_quota_dict')
    provider_id = serializers.Field(source='provider.id')

    class Meta:
        model = Identity
        exclude = ('credentials', 'created_by', 'provider')


class IdentityRelatedField(serializers.RelatedField):

    def to_native(self, identity):
        quota_dict = identity.get_quota_dict()
        return {
            "id": identity.id,
            "provider": identity.provider.location,
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

class AtmoUserSerializer(serializers.ModelSerializer):
    selected_identity = IdentityRelatedField(source='select_identity')

    def validate_selected_identity(self, attrs, source):
        """
        Check that profile is an identitymember & providermember
        Returns the dict of attrs
        """
        #Short-circut if source (identity) not in attrs
        logger.debug(attrs)
        logger.debug(source)
        if 'selected_identity' not in attrs:
            return attrs
        user = self.object.user
        logger.info("Validating identity for %s" % user)
        selected_identity = attrs['selected_identity']
        logger.debug(selected_identity)
        groups = user.group_set.all()
        for g in groups:
            for id_member in g.identitymembership_set.all():
                if id_member.identity == selected_identity:
                    logger.info("Saving new identity:%s" % selected_identity)
                    user.selected_identity = selected_identity
                    user.save()
                    return attrs
        raise serializers.ValidationError("User is not a member of"
                                          "selected_identity: %s"
                                          % selected_identity)


    class Meta:
        model = AtmosphereUser
        exclude = ('id','password')

class ProfileSerializer(serializers.ModelSerializer):
    """
    """
    #TODO:Need to validate provider/identity membership on id change
    username = serializers.CharField(read_only=True, source='user.username')
    email = serializers.CharField(read_only=True, source='email_hash')
    groups = serializers.CharField(read_only=True, source='user.groups.all')
    is_staff = serializers.BooleanField(source='user.is_staff')
    is_superuser = serializers.BooleanField(source='user.is_superuser')
    selected_identity = IdentityRelatedField(source='user.select_identity')

    class Meta:
        model = UserProfile
        exclude = ('id',)


class ProviderMachineSerializer(serializers.ModelSerializer):
    #R/O Fields first!
    alias = serializers.CharField(read_only=True, source='identifier')
    alias_hash = serializers.CharField(read_only=True, source='hash_alias')
    created_by = serializers.CharField(read_only=True,
                                       source='application.created_by.username')
    icon = serializers.CharField(read_only=True, source='icon_url')
    private = serializers.CharField(read_only=True, source='application.private')
    architecture = serializers.CharField(read_only=True,
                                         source='esh_architecture')
    ownerid = serializers.CharField(read_only=True, source='esh_ownerid')
    state = serializers.CharField(read_only=True, source='esh_state')
    scores = serializers.SerializerMethodField('get_scores')
    #Writeable fields
    name = serializers.CharField(source='application.name')
    tags = serializers.CharField(source='application.tags.all')
    description = serializers.CharField(source='application.description')
    start_date = serializers.CharField(source='start_date')
    end_date = serializers.CharField(source='end_date',
                                     required=False, read_only=True)
    featured = serializers.BooleanField(source='application.featured')
    version = serializers.CharField(source='version')

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop('request_user',None)
        super(ProviderMachineSerializer, self).__init__(*args, **kwargs)

    def get_scores(self, pm):
        app = pm.application
        scores = app.get_scores()
        update_dict = {
                "has_voted": False,
                "vote_cast": None
                }
        if not self.request_user:
            scores.update(update_dict)
            return scores
        last_vote = ApplicationScore.last_vote(app, self.request_user)
        if last_vote:
            update_dict["has_voted"] = True
            update_dict["vote_cast"] = last_vote.get_vote_name()
        scores.update(update_dict)
        return scores
    
    class Meta:
        model = ProviderMachine
        exclude = ('id', 'provider', 'application', 'identity')


class PaginatedProviderMachineSerializer(pagination.PaginationSerializer):
    """
    Serializes page objects of ProviderMachine querysets.
    """
    class Meta:
        object_serializer_class = ProviderMachineSerializer


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
    identity = CleanedIdentitySerializer(source="created_by_identity")

    class Meta:
        model = Volume
        exclude = ('id', 'created_by_identity', 'end_date')


class ProviderSizeSerializer(serializers.ModelSerializer):
    occupancy = serializers.CharField(read_only=True, source='esh_occupancy')
    total = serializers.CharField(read_only=True, source='esh_total')
    remaining = serializers.CharField(read_only=True, source='esh_remaining')
    active = serializers.BooleanField(read_only=True, source="active")

    class Meta:
        model = Size
        exclude = ('id', 'start_date', 'end_date')


class InstanceRelatedField(serializers.RelatedField):
    def to_native(self, instance_alias):
        instance = Instance.objects.get(provider_alias=instance_alias)
        return instance.provider_alias

    def field_from_native(self, data, files, field_name, into):
        value = data.get(field_name)
        if value is None:
            return
        try:
            into["instance"] = Instance.objects.get(provider_alias=value)
            into[field_name] = Instance.objects.get(provider_alias=value).provider_alias
        except Instance.DoesNotExist:
            into[field_name] = None


class StepSerializer(serializers.ModelSerializer):
    alias = serializers.CharField(read_only=True, source='alias')
    name = serializers.CharField()
    script = serializers.CharField()
    exit_code = serializers.IntegerField(read_only=True,
                                         source='exit_code')
    instance_alias = InstanceRelatedField(source='instance.provider_alias')
    created_by = serializers.SlugRelatedField(slug_field='username',
                                              source='created_by',
                                              read_only=True)
    start_date = serializers.DateTimeField(read_only=True)
    end_date = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Step
        exclude = ('id', 'instance', 'created_by_identity')


class ProviderTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderType


class TagSerializer(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(slug_field='username')
    description = serializers.CharField(required=False)

    class Meta:
        model = Tag
