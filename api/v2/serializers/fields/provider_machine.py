from rest_framework import serializers
from api.v2.serializers.summaries import ProviderMachineSummarySerializer


class ProviderMachineRelatedField(serializers.RelatedField):

    def __init__(self, **kwargs):
        kwargs['read_only'] = True
        super(ProviderMachineRelatedField, self).__init__(**kwargs)

    def to_representation(self, value):
        serializer = ProviderMachineSummarySerializer(
            value,
            context=self.context)
        return serializer.data
