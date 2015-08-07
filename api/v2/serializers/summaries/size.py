from core.models import Size
from rest_framework import serializers

class SizeSummarySerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Size
        view_name = 'api:v2:size-detail'
        fields = (
            'id',
            'url',
            'alias',
            'name',
            'cpu',
            'disk',
            'mem',
            'active',
            'start_date',
            'end_date')

class SizeRelatedField(serializers.PrimaryKeyRelatedField):

    def get_queryset(self):
        return Size.objects.all()

    def to_representation(self, value):
        size = Size.objects.get(pk=value.pk)
        serializer = SizeSummarySerializer(
            size,
            context=self.context)
        return serializer.data

