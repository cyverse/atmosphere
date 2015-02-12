from core.models import Identity
from rest_framework import serializers
from .quota import QuotaSerializer
from .allocation import AllocationSerializer
from .user import UserSerializer


class IdentitySerializer(serializers.HyperlinkedModelSerializer):
    quota = QuotaSerializer(source='get_quota')
    allocation = AllocationSerializer(source='get_allocation')
    user = UserSerializer(source='created_by')

    class Meta:
        model = Identity
        view_name = 'api_v2:identity-detail'
        fields = ('id', 'url', 'quota', 'allocation', 'user')


class IdentitySummarySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Identity
        view_name = 'api_v2:identity-detail'
        fields = ('id',)
