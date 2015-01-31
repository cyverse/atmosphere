from core.models import Identity
from rest_framework import serializers
from .quota_serializer import QuotaSerializer
from .allocation_serializer import AllocationSerializer
from .user_serializer import UserSerializer


class IdentitySerializer(serializers.ModelSerializer):
    quota = QuotaSerializer(source='get_quota.__dict__')
    allocation = AllocationSerializer(source='get_allocation.__dict__')
    user = UserSerializer(source='created_by')

    class Meta:
        model = Identity
        fields = ('id', 'quota', 'allocation', 'user')
