from rest_framework import serializers

from threepio import logger

from core.models.cloud_admin import CloudAdministrator


class CloudAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = CloudAdministrator


class CloudAdminActionListSerializer(serializers.ModelSerializer):
    imaging_request = serializers.HyperlinkedIdentityField(
        view_name='cloud-admin-imaging-request',
        lookup_field='uuid')

    class Meta:
        model = CloudAdministrator
        fields = (
            # 'provider_status',
            # 'provider_disable',
            # 'provider_enable',
            # # Represented as user -- Actually an identity!
            # 'user_list',
            # 'user_disable',
            # 'user_enable',
            # # Additional admin functionality
            # 'create_account',
            # 'over_allocation_policy',
            # 'quota_request',
            # 'allocation_request',
            'imaging_request',
        )
