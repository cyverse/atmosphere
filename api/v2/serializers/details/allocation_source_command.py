
from rest_framework import serializers

class AllocationSourceCommandSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(max_length=256)
    desc = serializers.CharField()
