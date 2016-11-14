from core.models.profile import UserProfile
from core.models import Identity
from rest_framework import serializers
from .identity_related_field import IdentityRelatedField


class ProfileSerializer(serializers.ModelSerializer):

    """
    """
    # TODO:Need to validate provider/identity membership on id change
    username = serializers.CharField(read_only=True, source='user.username')
    email = serializers.CharField(read_only=True, source='user.email')
    groups = serializers.CharField(read_only=True, source='user.groups.all')
    is_expired = serializers.BooleanField(source='user.is_expired')
    is_staff = serializers.BooleanField(source='user.is_staff')
    is_superuser = serializers.BooleanField(source='user.is_superuser')
    selected_identity = IdentityRelatedField(
        source='user.select_identity',
        queryset=Identity.objects.all())

    class Meta:
        model = UserProfile
        fields = '__all__'
