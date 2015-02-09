from core.models import Identity
from rest_framework import serializers
from .quota_serializer import QuotaSerializer
from .allocation_serializer import AllocationSerializer
from .user_serializer import UserSerializer


class IdentitySerializer(serializers.HyperlinkedModelSerializer):
    quota = QuotaSerializer(source='get_quota.__dict__')
    allocation = AllocationSerializer(source='get_allocation')
    user = UserSerializer(source='created_by')

    class Meta:
        model = Identity
        view_name = 'api_v2:identity-detail'
        fields = ('id', 'url', 'quota', 'allocation', 'user')
