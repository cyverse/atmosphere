from core.models import ApplicationVersion as ImageVersion
from rest_framework import serializers
from api.v2.serializers.summaries import (
    LicenseSummarySerializer,
    UserSummarySerializer,
    IdentitySummarySerializer,
    ImageVersionSummarySerializer)
from api.v2.serializers.fields import ProviderMachineRelatedField


class ImageVersionSerializer(serializers.HyperlinkedModelSerializer):

    """
    Serializer for ApplicationVersion (aka 'image_version')
    """
    # NOTE: Implicitly included via 'fields'
    # id, application
    parent = ImageVersionSummarySerializer()
    # name, change_log, allow_imaging
    licenses = LicenseSummarySerializer(many=True, read_only=True)  # NEW
    membership = serializers.SlugRelatedField(
        slug_field='name',
        read_only=True,
        many=True)  # NEW
    user = UserSummarySerializer(source='created_by')
    identity = IdentitySummarySerializer(source='created_by_identity')
    machines = ProviderMachineRelatedField(many=True)
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField(required=False)

    class Meta:
        model = ImageVersion
        view_name = 'api:v2:providermachine-detail'
        fields = ('id', 'parent', 'name', 'change_log',
                  'machines', 'allow_imaging',
                  'licenses', 'membership',
                  'user', 'identity',
                  'start_date', 'end_date')
