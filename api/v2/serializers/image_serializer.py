from core.models import Application as Image
from rest_framework import serializers
from .user_serializer import UserSerializer
from .tag_serializer import TagSerializer
from .provider_machine_summary_serializer import ProviderMachineSummarySerializer


class MachineProviderRelatedField(serializers.RelatedField):

    def __init__(self, **kwargs):
        kwargs['read_only'] = True
        super(MachineProviderRelatedField, self).__init__(**kwargs)

    def to_representation(self, value):
        serializer = ProviderMachineSummarySerializer(value)
        return serializer.data


class ImageSerializer(serializers.ModelSerializer):
    # todo: add created by field w/ user
    # todo: add tags
    created_by = UserSerializer()
    tags = TagSerializer(many=True)
    provider_images = MachineProviderRelatedField(source='providermachine_set', many=True)
    # machine_count = serializers.SerializerMethodField()
    machine_count = serializers.IntegerField(
        source='providermachine_set.count',
        read_only=True
    )

    # def get_machine_count(self, obj):
    #     return obj.providermachine_set.count()

    class Meta:
        model = Image
        fields = ('id', 'uuid', 'name', 'description', 'icon', 'created_by', 'tags', 'start_date', 'end_date', 'provider_images', 'machine_count')
