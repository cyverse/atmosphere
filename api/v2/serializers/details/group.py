from core.models import (
    Group, GroupMembership, AtmosphereUser, IdentityMembership
)
from rest_framework import serializers
from api.v2.serializers.fields.base import (
    ModelRelatedField,
    UUIDHyperlinkedIdentityField
)
from api.v2.serializers.summaries import UserSummarySerializer


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:group-detail',
    )
    users = ModelRelatedField(
        queryset=AtmosphereUser.objects.all(),
        serializer_class=UserSummarySerializer,
        source='get_users',
        style={'base_template': 'input.html'},
        many=True,
        lookup_field='username')
    leaders = ModelRelatedField(
        queryset=AtmosphereUser.objects.all(),
        serializer_class=UserSummarySerializer,
        source='get_leaders',
        lookup_field='username',
        style={'base_template': 'input.html'},
        many=True,
        required=False)

    def add_identity_memberships(self, group):
        for member in group.memberships.all():
            user = member.user
            [
                IdentityMembership.objects.get_or_create(
                    identity=ident,
                    member=group)
                for ident in user.identity_set.all()
            ]
        return

    def update_group_membership(self, group, users, leaders):
        for user in users:
            GroupMembership.objects.create(
                group=group,
                user=user
            )
            group.user_set.add(user)
        for user in leaders:
            GroupMembership.objects.create(
                group=group,
                user=user,
                is_leader=True
            )
            group.user_set.add(user)
        return

    def _get_request_user(self, raise_exception=True):
        if 'request' in self.context:
            return self.context['request'].user
        elif 'user' in self.context:
            return self.context['user']
        elif raise_exception:
            raise serializers.ValidationError("Expected 'request' or 'user' to be passed in via context for this serializer")
        return None


    def update(self, group, validated_data):
        user = self._get_request_user(True)
        if not user.is_staff and not group.leaders.filter(user=user).exists():
            raise serializers.ValidationError("User %s is not a project leader" % user.username)
        cleaned_data = {}

        # Leaders are 'flagged' and users are not.
        if 'get_users' in validated_data and 'get_leaders' in validated_data:
            leaders = validated_data.get('get_leaders', [])
            users = [user for user in validated_data.get('get_users',[]) if user not in leaders]

            # TODO: Efficient update? users and leaders might be added/removed..
            group.user_set.remove()
            group.memberships.all().delete()
            self.update_group_membership(group, users, leaders)
        elif 'get_users' in validated_data or 'get_leaders' in validated_data:
            raise serializers.ValidationError(
                "To update the membership, pass _both_ 'users' and 'leaders'")

        group.identity_memberships.all().delete()
        self.add_identity_memberships(group)

        return super(GroupSerializer, self).update(group, cleaned_data)

    def create(self, validated_data):
        user = self._get_request_user(True)
        if not user.is_staff:
            raise serializers.ValidationError("Only staff users can create groups.")

        group_kwargs = validated_data.copy()

        # Leaders are 'flagged' and users are not.
        leaders = group_kwargs.pop('get_leaders')
        users = [user for user in group_kwargs.pop('get_users') if user not in leaders]

        new_group = Group.objects.create(**group_kwargs)
        self.update_group_membership(new_group, users, leaders)
        self.add_identity_memberships(new_group)
        return new_group

    class Meta:
        model = Group
        fields = (
            'id',
            'uuid',
            'url',
            'name',
            'users',
            'leaders',
        )
