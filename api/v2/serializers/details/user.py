from core.models.user import AtmosphereUser
from rest_framework import serializers
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class UserSerializer(serializers.HyperlinkedModelSerializer):
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:atmosphereuser-detail',
    )

    class Meta:
        model = AtmosphereUser
        fields = (
            'id',
            'uuid',
            'url',
            'username',
            'end_date',
            # 'first_name',
            # 'last_name',
            # 'email',
            # 'is_staff',
            # 'is_superuser',
            # 'date_joined'
        )

class AdminUserSerializer(serializers.HyperlinkedModelSerializer):
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:atmosphereuser-detail',
    )

    class Meta:
        model = AtmosphereUser
        fields = (
            'id',
            'uuid',
            'url',
            'username',
            'end_date',
            'is_active',
            'is_staff',
            'is_superuser',
            'email',
            # 'first_name',
            # 'last_name',
            # 'date_joined'
        )
