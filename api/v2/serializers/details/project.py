from core.models import Project, Group, AtmosphereUser
from rest_framework.exceptions import ValidationError
from rest_framework import serializers
from api.v2.serializers.summaries import (
    InstanceSummarySerializer, VolumeSummarySerializer,
    ImageSummarySerializer, ExternalLinkSummarySerializer,
    GroupSummarySerializer, UserSummarySerializer
)
from api.v2.serializers.fields import ModelRelatedField
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField



class ProjectSerializer(serializers.HyperlinkedModelSerializer):
    images = ImageSummarySerializer(
            source='applications', many=True, read_only=True)
    instances = InstanceSummarySerializer(
            source='active_instances', many=True, read_only=True)
    links = ExternalLinkSummarySerializer(
            many=True, read_only=True)
    volumes = VolumeSummarySerializer(
            source='active_volumes', many=True, read_only=True)
    # note: both of these requests become a single DB query, but I'm choosing
    # the owner.name route so the API doesn't break when we start adding users
    # to groups owner = UserSerializer(source='owner.user_set.first')
    created_by = ModelRelatedField(
        lookup_field="username",
        default=serializers.CurrentUserDefault(),
        queryset=AtmosphereUser.objects.all(),
        serializer_class=UserSummarySerializer,
        style={'base_template': 'input.html'})
    owner = ModelRelatedField(
        lookup_field="name",
        queryset=Group.objects.all(),
        serializer_class=GroupSummarySerializer,
        style={'base_template': 'input.html'})
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:project-detail',
    )
    users = UserSummarySerializer(source='get_users', many=True, read_only=True)
    leaders = UserSummarySerializer(source='get_leaders', many=True, read_only=True)

    def update(self, instance, validated_data):
        """
        Check that project does not have shared resources.
        If so, do not allow owner changes.
        """
        new_owner = validated_data.get('owner')
        current_owner = instance.owner
        if new_owner and current_owner != new_owner:
            self.validate_ownership(instance, current_owner)
        return super(ProjectSerializer, self).update(instance, validated_data)

    def validate_ownership(self, project, current_owner):
        if project.has_shared_resources():
            raise ValidationError(
                "Cannot update ownership for a project when it contains "
                "shared cloud resources. To update project ownership, "
                "all shared cloud resources must be "
                "moved to another project or deleted"
            )
        request = self.context.get('request')
        if not request:
            return True
        request_user = request.user
        if request_user not in project.get_leaders():
            raise ValidationError(
                "This project has been shared with you. "
                "To change a projects ownership, "
                "you must be the project owner."
            )
        return True

    class Meta:
        model = Project
        fields = (
            'id',
            'uuid',
            'url',
            'name',
            'description',
            'created_by',
            'owner',
            'users',
            'leaders',
            'instances',
            'images',
            'links',
            'volumes',
            'start_date',
            'end_date'
        )
