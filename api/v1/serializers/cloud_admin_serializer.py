from rest_framework import serializers

from threepio import logger
from core.models.user import AtmosphereUser
from core.models.provider import Provider
from core.models.cloud_admin import CloudAdministrator


class CloudAdminSerializer(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(
        slug_field='username', queryset=AtmosphereUser.objects.all())
    provider = serializers.SlugRelatedField(
        slug_field='uuid', queryset=Provider.objects.all())

    class Meta:
        model = CloudAdministrator
        exclude = ("id",)


class CloudAdminActionListSerializer(serializers.ModelSerializer):
    user_list = serializers.HyperlinkedIdentityField(
        view_name='api:v1:cloud-admin-account-list',
        lookup_field='uuid', lookup_url_kwarg="cloud_admin_uuid")
    #    lookup_field='uuid', lookup_url_kwarg="cloud_admin_uuid")
    imaging_request = serializers.HyperlinkedIdentityField(
        view_name='api:v1:cloud-admin-imaging-request-list',
        lookup_field='uuid', lookup_url_kwarg="cloud_admin_uuid")

    class Meta:
        model = CloudAdministrator
        fields = (
            # 'provider_status',
            # 'provider_disable',
            # 'provider_enable',
            # Represented to admin as 'user'
            # But is  Actually an identity!
            'user_list',
            # 'user_enable',
            # # Additional admin functionality
            # 'create_account',
            # 'over_allocation_policy',
            'imaging_request',
        )
