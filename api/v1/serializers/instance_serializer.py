from core.models.instance import Instance
from core.models.instance_action import InstanceAction
from core.models import Tag
from rest_framework import serializers
from .cleaned_identity_serializer import CleanedIdentitySerializer
from .tag_related_field import TagRelatedField
from .projects_field import ProjectsField
from .boot_script_serializer import BootScriptSerializer
from .get_context_user import get_context_user


class InstanceSerializer(serializers.ModelSerializer):
    # R/O Fields first!
    alias = serializers.CharField(read_only=True, source='provider_alias')
    alias_hash = serializers.CharField(read_only=True, source='hash_alias')
    application_name = serializers.CharField(
        read_only=True, source='esh_source_name')
    application_uuid = serializers.CharField(read_only=True)
    created_by = serializers.SlugRelatedField(
        slug_field='username',
        read_only=True)
    status = serializers.CharField(read_only=True, source='esh_status')
    activity = serializers.CharField(read_only=True, source='esh_activity')
    fault = serializers.ReadOnlyField(source='esh_fault')
    size_alias = serializers.CharField(read_only=True, source='esh_size')
    machine_alias = serializers.CharField(read_only=True, source='esh_source')
    machine_name = serializers.CharField(read_only=True,
                                         source='esh_source_name')
    machine_alias_hash = serializers.CharField(read_only=True,
                                               source='hash_machine_alias')
    ip_address = serializers.CharField(read_only=True)
    start_date = serializers.DateTimeField(read_only=True)
    end_date = serializers.DateTimeField(read_only=True)
    token = serializers.CharField(read_only=True)
    has_shell = serializers.BooleanField(read_only=True, source='shell')
    has_vnc = serializers.BooleanField(read_only=True, source='vnc')
    identity = CleanedIdentitySerializer(source="created_by_identity",
                                         read_only=True)
    # Writeable fields
    name = serializers.CharField()
    tags = TagRelatedField(
        slug_field='name',
        required=False,
        many=True,
        queryset=Tag.objects.all())
    projects = ProjectsField(required=False)
    scripts = BootScriptSerializer(many=True, required=False)

    def __init__(self, *args, **kwargs):
        user = get_context_user(self, kwargs)
        self.request_user = user
        super(InstanceSerializer, self).__init__(*args, **kwargs)

    class Meta:
        model = Instance
        exclude = ('source', 'provider_alias',
                   'shell', 'vnc', 'password', 'created_by_identity')


class InstanceActionSerializer(serializers.ModelSerializer):

    class Meta:
        model = InstanceAction
