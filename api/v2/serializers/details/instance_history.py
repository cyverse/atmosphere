from rest_framework import serializers

from allocation.models import Instance as AllocInstance
from allocation.engine import calculate_allocation
from allocation.models import Allocation
from core.models import Instance, InstanceStatusHistory, Size

from api.v2.serializers.summaries import (
    InstanceSuperSummarySerializer,
    ProviderSummarySerializer, ImageSummarySerializer)
from api.v2.serializers.summaries.size import SizeRelatedField
from api.v2.serializers.fields.base import (
    ModelRelatedField, UUIDHyperlinkedIdentityField
)


class InstanceStatusHistorySerializer(serializers.HyperlinkedModelSerializer):
    instance = ModelRelatedField(
        queryset=Instance.objects.all(),
        serializer_class=InstanceSuperSummarySerializer,
        style={'base_template': 'input.html'})
    size = SizeRelatedField(queryset=Size.objects.none())
    provider = ProviderSummarySerializer(
        source='instance.get_provider')
    image = ImageSummarySerializer(
        source='instance.provider_machine.application_version.application')
    status = serializers.SlugRelatedField(slug_field='name', read_only=True)
    activity = serializers.CharField(max_length=36, allow_blank=True)
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:instancestatushistory-detail',
    )

    class Meta:
        model = InstanceStatusHistory
        fields = (
            'id',
            'uuid',
            'url',
            'instance',
            'status',
            'activity',
            'size',
            'provider',
            'image',
            'start_date',
            'end_date',
        )
