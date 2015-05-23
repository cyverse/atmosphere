from core.models.user import AtmosphereUser
from rest_framework import serializers


class UserSummarySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = AtmosphereUser
        view_name = 'api:v2:atmosphereuser-detail'
        fields = (
                'id',
                'url',
                'username',
                #'first_name',
                #'last_name',
                #'email',
                #'is_staff',
                #'is_superuser',
                #'date_joined'
        )
