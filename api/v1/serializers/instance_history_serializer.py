from core.models.instance import Instance
from core.models import Tag
from rest_framework import serializers
from .tag_related_field import TagRelatedField


class InstanceHistorySerializer(serializers.ModelSerializer):
    # R/O Fields first!
    alias = serializers.CharField(read_only=True, source='provider_alias')
    alias_hash = serializers.CharField(read_only=True, source='hash_alias')
    created_by = serializers.SlugRelatedField(slug_field='username',
                                              read_only=True)
    size_alias = serializers.CharField(read_only=True, source='esh_size')
    # NOTE: Now that we have moved to 'source', this can be a bit of a
    # misnomer.. New API should correct this representation.
    machine_alias = serializers.CharField(read_only=True, source='esh_source')
    machine_name = serializers.CharField(read_only=True,
                                         source='esh_source_name')
    machine_alias_hash = serializers.CharField(read_only=True,
                                               source='hash_machine_alias')
    application_uuid = serializers.CharField(read_only=True,)
    application_id = serializers.IntegerField(read_only=True,)
    # ENDNOTE
    ip_address = serializers.CharField(read_only=True)
    start_date = serializers.DateTimeField(read_only=True)
    end_date = serializers.DateTimeField(read_only=True)
    provider = serializers.CharField(read_only=True, source='provider_name')
    # Writeable fields
    name = serializers.CharField()
    tags = TagRelatedField(
        slug_field='name',
        many=True,
        queryset=Tag.objects.all())

    class Meta:
        model = Instance
        exclude = ('id', 'source', 'provider_alias',
                   'shell', 'vnc', 'created_by_identity')
