from core.models.export_request import ExportRequest
from core.models.user import AtmosphereUser
from core.models.instance import Instance
from rest_framework import serializers


class ExportRequestSerializer(serializers.ModelSerializer):

    """
    """
    name = serializers.CharField(source='export_name')
    instance = serializers.SlugRelatedField(
        slug_field='provider_alias',
        queryset=Instance.objects.all()
    )
    status = serializers.CharField(default="pending")
    disk_format = serializers.CharField(source='export_format')
    owner = serializers.SlugRelatedField(slug_field='username',
                                         source='export_owner',
                                         queryset=AtmosphereUser.objects.all()
                                         )
    file = serializers.CharField(read_only=True, default="",
                                 required=False, source='export_file')

    class Meta:
        model = ExportRequest
        fields = ('id', 'instance', 'status', 'name',
                  'owner', 'disk_format', 'file')
