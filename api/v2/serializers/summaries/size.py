from core.models import Size
from rest_framework import serializers
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class SizeSummarySerializer(serializers.HyperlinkedModelSerializer):
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:size-detail',
    )
    class Meta:
        model = Size
        fields = (
            'id',
            'uuid',
            'url',
            'alias',
            'name',
            'cpu',
            'disk',
            'mem',
            'active',
            'start_date',
            'end_date')
#TODO: Move to fields?
class SizeRelatedField(serializers.PrimaryKeyRelatedField):

    def get_queryset(self):
        return Size.objects.all()

    def to_representation(self, value):
        size = Size.objects.get(pk=value.pk)
        serializer = SizeSummarySerializer(
            size,
            context=self.context)
        return serializer.data

