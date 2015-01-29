from core.models.application import ApplicationScore
from core.models.group import Group
from core.models.quota import Quota
from core.models.allocation import Allocation
from core.models.identity import Identity
from core.models.instance import InstanceStatusHistory
from core.models.machine import ProviderMachine
from core.models.project import Project
from core.models.provider import ProviderType
from core.models.request import AllocationRequest, QuotaRequest, StatusType
from core.models.size import Size
from core.models.step import Step
from core.models.tag import Tag
from core.models.user import AtmosphereUser
from core.models.volume import Volume
from core.query import only_current

from rest_framework import serializers

from rest_framework import pagination


# Serializers
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
                   {"id": i.uuid, "provider_id": i.provider.uuid},
                   identities)


class VolumeSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True, source='get_status')
    attach_data = serializers.Field(source='esh_attach_data')
    #metadata = serializers.Field(source='esh_metadata')
    mount_location = serializers.Field(source='mount_location')
    created_by = serializers.SlugRelatedField(slug_field='username',
                                              source='created_by',
                                              read_only=True)
    provider = serializers.Field(source="provider.uuid")
    identity = CleanedIdentitySerializer(source="created_by_identity")
    projects = ProjectsField()

    def __init__(self, *args, **kwargs):
        user = get_context_user(self, kwargs)
        self.request_user = user
        super(VolumeSerializer, self).__init__(*args, **kwargs)

    class Meta:
        model = Volume
        exclude = ('id', 'created_by_identity', 'end_date')


class NoProjectSerializer(serializers.ModelSerializer):
    applications = serializers.SerializerMethodField('get_user_applications')
    instances = serializers.SerializerMethodField('get_user_instances')
    volumes = serializers.SerializerMethodField('get_user_volumes')

    def get_user_applications(self, atmo_user):
        return [ApplicationSerializer(
            item,
            context={'request': self.context.get('request')}).data for item in
            atmo_user.application_set.filter(only_current(), projects=None)]

    def get_user_instances(self, atmo_user):
        return [InstanceSerializer(
            item,
            context={'request': self.context.get('request')}).data for item in
            atmo_user.instance_set.filter(only_current(),
                source__provider__active=True,
                projects=None)]

    def get_user_volumes(self, atmo_user):
        return [VolumeSerializer(
            item,
            context={'request': self.context.get('request')}).data for item in
            atmo_user.volume_set().filter(only_current(), 
                provider__active=True, projects=None)]
    class Meta:
        model = AtmosphereUser
        fields = ('applications', 'instances', 'volumes')

class ProjectSerializer(serializers.ModelSerializer):
    id = serializers.Field(source="uuid")
    #Edits to Writable fields..
    owner = serializers.SlugRelatedField(slug_field="name")
    # These fields are READ-ONLY!
    applications = serializers.SerializerMethodField('get_user_applications')
    instances = serializers.SerializerMethodField('get_user_instances')
    volumes = serializers.SerializerMethodField('get_user_volumes')

    def get_user_applications(self, project):
        return [ApplicationSerializer(
            item,
            context={'request': self.context.get('request')}).data for item in
            project.applications.filter(only_current())]

    def get_user_instances(self, project):
        return [InstanceSerializer(
            item,
            context={'request': self.context.get('request')}).data for item in
            project.instances.filter(only_current(),
                source__provider__active=True
                )]

    def get_user_volumes(self, project):
        return [VolumeSerializer(
            item,
            context={'request': self.context.get('request')}).data for item in
            project.volumes.filter(only_current(), provider__active=True)]

    def __init__(self, *args, **kwargs):
        user = get_context_user(self, kwargs)
        super(ProjectSerializer, self).__init__(*args, **kwargs)

    class Meta:
        model = Project
        exclude = ('uuid', )


class ProviderSizeSerializer(serializers.ModelSerializer):
    occupancy = serializers.CharField(read_only=True, source='esh_occupancy')
    total = serializers.CharField(read_only=True, source='esh_total')
    remaining = serializers.CharField(read_only=True, source='esh_remaining')
    active = serializers.BooleanField(read_only=True, source="active")

    class Meta:
        model = Size
        exclude = ('id', 'start_date', 'end_date')


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


class InstanceStatusHistorySerializer(serializers.ModelSerializer):
    instance = serializers.SlugRelatedField(slug_field='provider_alias')
    size = serializers.SlugRelatedField(slug_field='alias')

    class Meta:
        model = InstanceStatusHistory


class AllocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Allocation


class AllocationRequestSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True, source="uuid")
    created_by = serializers.SlugRelatedField(
        slug_field='username', source='created_by', read_only=True)
    status = serializers.SlugRelatedField(
        slug_field='name', source='status', read_only=True)

    class Meta:
        model = AllocationRequest
        exclude = ('uuid', 'membership')


class QuotaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quota
        exclude = ("id",)


class QuotaRequestSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True, source="uuid", required=False)
    created_by = serializers.SlugRelatedField(
        slug_field='username', source='created_by',
        queryset=AtmosphereUser.objects.all())
    status = serializers.SlugRelatedField(
        slug_field='name', source='status',
        queryset=StatusType.objects.all())

    class Meta:
        model = QuotaRequest
        exclude = ('uuid', 'membership')


class IdentitySerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source='creator_name')
    credentials = serializers.Field(source='get_credentials')
    id = serializers.Field(source='uuid')
    provider_id = serializers.Field(source='provider_uuid')
    quota = QuotaSerializer(source='get_quota')
    allocation = AllocationSerializer(source='get_allocation')
    membership = serializers.Field(source='get_membership')

    class Meta:
        model = Identity
        fields = ('id', 'created_by', 'provider_id', 'credentials',
                  'membership', 'quota', 'allocation')
