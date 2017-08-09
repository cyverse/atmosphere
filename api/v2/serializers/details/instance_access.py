from rest_framework import serializers

from core.models import (
    AtmosphereUser,
    InstanceAccess,
    StatusType,
    Instance
)
from core.events.serializers.instance_access import AddInstanceAccessSerializer, RemoveInstanceAccessSerializer
from api.v2.serializers.summaries import (
    InstanceSuperSummarySerializer,
    StatusTypeSummarySerializer,
    UserSummarySerializer
)

from api.v2.serializers.fields import (
    ModelRelatedField
)
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class InstanceAccessSerializer(serializers.HyperlinkedModelSerializer):

    instance = ModelRelatedField(
        lookup_field="provider_alias",
        queryset=Instance.objects.all(),
        serializer_class=InstanceSuperSummarySerializer,
        style={'base_template': 'input.html'})
    user = ModelRelatedField(
        lookup_field="username",
        queryset=AtmosphereUser.objects.all(),
        serializer_class=UserSummarySerializer,
        style={'base_template': 'input.html'})
    status = serializers.SlugRelatedField(
        slug_field='name', default="pending",
        queryset=StatusType.objects.all()
    )
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:instanceaccess-detail',
        uuid_field='id'
    )

    def get_context_user(self):
        user = None
        if self.context:
            if 'request' in self.context:
                user = self.context['request'].user
            elif 'user' in self.context:
                user = self.context['user']
        return user

    def validate_status(self, value):
        status = StatusType.objects.filter(name=value).first()
        if not status:
            raise serializers.ValidationError(
                "Unknown status type: %s" % value)
        if self.instance:
            instance_access = self.instance
            instance_access.status = status
            current_user = self.get_context_user()
            if status.name == 'approved':
                if current_user != instance_access.user:
                    raise serializers.ValidationError(
                        "Only user %s can approve the request for Instance Access"
                        % instance_access.user)
        return status

    def update(self, instance_access, validated_data):
        """
        On status update:
          Fire off an event hook, ensure it works, then set to approved.
        """
        # TEST: the right user is updating this.
        status = validated_data['status']
        instance_access.status = status
        if status.name == 'approved':
            serializer = AddInstanceAccessSerializer(data={
                'user': instance_access.user.username,
                'instance': instance_access.instance.provider_alias
            })
            if not serializer.is_valid():
                errors = serializer.errors
                raise Exception(
                    "Error occurred while adding instance_access for "
                    "Instance:%s, User:%s -- %s"
                    % (
                        instance_access.instance,
                        instance_access.user,
                        errors))
            serializer.save()
        elif status.name == "cancelled":  # FIXME: Naming?
            serializer = RemoveInstanceAccessSerializer(data={
                'user': instance_access.user.username,
                'instance': instance_access.instance.provider_alias
            })
            if not serializer.is_valid():
                errors = serializer.errors
                raise Exception(
                    "Error occurred while removing instance_access for "
                    "Instance:%s, Username:%s -- %s"
                    % (
                        instance_access.instance,
                        instance_access.user,
                        errors))
            serializer.save()
        return instance_access

    class Meta:
        model = InstanceAccess
        fields = (
            'id',
            'instance',
            'status',
            'user',
            'url',
        )


class UserInstanceAccessSerializer(InstanceAccessSerializer):

    def validate_status(self, value):
        if self.instance and str(value) not in ["approved", "denied", "cancelled"]:
            raise serializers.ValidationError("Users can only approve, deny, and cancel instance access requests.")
        elif not self.instance and str(value) != "pending":
            raise serializers.ValidationError("Only 'pending' status is valid when creating an InstanceAccess request.")
        return super(UserInstanceAccessSerializer, self).validate_status(value)
