from core.models.instance import InstanceStatusHistory, Instance
from core.models import Size
from rest_framework import serializers


class InstanceStatusHistorySerializer(serializers.ModelSerializer):
    instance = serializers.SlugRelatedField(
        slug_field='provider_alias',
        queryset=Instance.objects.all())
    size = serializers.SlugRelatedField(
        slug_field='alias',
        queryset=Size.objects.all())

    class Meta:
        model = InstanceStatusHistory
