from core.models import Project
from rest_framework import serializers
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class ProjectSummarySerializer(serializers.HyperlinkedModelSerializer):
    created_by = serializers.StringRelatedField(source='created_by.username')
    owner = serializers.StringRelatedField(source='owner.name')
    shared_with_me = serializers.SerializerMethodField()
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:project-detail',
    )

    def get_shared_with_me(self, project):
        """
        """
        current_user = self.get_context_user()
        leaders = project.get_leaders()
        return leaders.filter(id=current_user.id).count() == 0

    def get_context_user(self):
        user = None
        if self.context:
            if 'request' in self.context:
                user = self.context['request'].user
            elif 'user' in self.context:
                user = self.context['user']
        return user

    class Meta:
        model = Project
        fields = (
            'id',
            'url',
            'uuid',
            'name',
            'description',
            'owner',
            'shared_with_me',
            'created_by',
            'start_date',
            'end_date'
        )
