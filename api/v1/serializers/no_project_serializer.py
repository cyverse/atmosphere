from core.models.user import AtmosphereUser
from core.query import only_current, only_current_source
from rest_framework import serializers
from .application_serializer import ApplicationSerializer
from .instance_serializer import InstanceSerializer
from .volume_serializer import VolumeSerializer


class NoProjectSerializer(serializers.ModelSerializer):
    applications = serializers.SerializerMethodField('get_user_applications')
    instances = serializers.SerializerMethodField('get_user_instances')
    volumes = serializers.SerializerMethodField('get_user_volumes')

    def get_user_applications(self, atmo_user):
        return [ApplicationSerializer(
            item,
            context={'request': self.context.get('request')}).data for item in
            atmo_user.application_set.filter(only_current(), projects=None)]

    def get_user_instances(self, atmo_user):
        return [InstanceSerializer(
            item,
            context={'request': self.context.get('request')}).data for item in
            atmo_user.instance_set.filter(only_current(),
                source__provider__active=True,
                projects=None)]

    def get_user_volumes(self, atmo_user):
        return [VolumeSerializer(
            item,
            context={'request': self.context.get('request')}).data for item in
            atmo_user.volume_set().filter(only_current_source(),
                instance_source__provider__active=True, projects=None)]

    class Meta:
        model = AtmosphereUser
        fields = ('applications', 'instances', 'volumes')
