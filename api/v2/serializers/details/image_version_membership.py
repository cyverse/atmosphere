from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from core.models import ApplicationVersionMembership as ImageVersionMembership
from core.models import ApplicationVersion as ImageVersion
from core.models import Group as Membership

from api.v2.serializers.summaries import (
    ImageVersionSummarySerializer, GroupSummarySerializer)
from api.v2.serializers.fields.base import ModelRelatedField


class ImageVersionMembershipSerializer(serializers.HyperlinkedModelSerializer):
    image_version = ModelRelatedField(
        queryset=ImageVersion.objects.all(),
        serializer_class=ImageVersionSummarySerializer,
        style={'base_template': 'input.html'},
        required=False)
    #NOTE: When complete, return here to disambiguate between 'membership'&&'group'
    group = ModelRelatedField(
        queryset=Membership.objects.all(),
        serializer_class=GroupSummarySerializer,
        style={'base_template': 'input.html'},
        lookup_field='uuid',
        required=False)
    url = serializers.HyperlinkedIdentityField(
        view_name='api:v2:imageversion_membership-detail',
    )

    class Meta:
        model = ImageVersionMembership
        validators = [
            UniqueTogetherValidator(
                queryset=ImageVersionMembership.objects.all(),
                fields=('image_version', 'group')
            )
        ]
        fields = (
            'id',
            'url',
            'image_version',
            'group'
        )
