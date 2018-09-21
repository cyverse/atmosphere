from core.models import SSHKey
from rest_framework import serializers


class SSHKeySerializer(serializers.ModelSerializer):

    uuid = serializers.CharField(max_length=36, read_only=True)

    class Meta:
        model = SSHKey
        fields = "__all__"
