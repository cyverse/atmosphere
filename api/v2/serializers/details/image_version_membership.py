from rest_framework import serializers

from core.models import ApplicationVersionMembership as ImageVersionMembership
from core.models import ApplicationVersion as ImageVersion
from core.models import Group as Membership

from api.v2.serializers.summaries import (
    ImageVersionSummarySerializer, MembershipSummarySerializer)


class ImageVersionRelatedField(serializers.PrimaryKeyRelatedField):

    def get_queryset(self):
        return ImageVersion.objects.all()

    def to_representation(self, value):
        image_version = ImageVersion.objects.get(pk=value.pk)
        serializer = ImageVersionSummarySerializer(
            image_version,
            context=self.context)
        return serializer.data


class MembershipRelatedField(serializers.PrimaryKeyRelatedField):

    def get_queryset(self):
        return Membership.objects.all()

    def to_representation(self, value):
        membership = Membership.objects.get(pk=value.pk)
        serializer = MembershipSummarySerializer(membership, context=self.context)
        return serializer.data


class ImageVersionMembershipSerializer(serializers.HyperlinkedModelSerializer):
    image_version = ImageVersionRelatedField(
        queryset=ImageVersion.objects.none(), source='application_version')
    group = MembershipRelatedField(
        queryset=Membership.objects.none())

    class Meta:
        model = ImageVersionMembership
        view_name = 'api:v2:imageversion_membership-detail'
        fields = (
            'id',
            'url',
            'image_version',
            'group'
        )
