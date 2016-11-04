from rest_framework import serializers

from api.v2.serializers.summaries import (
    SizeSummarySerializer,
)
from core.models import (
    Instance
)


class InstanceReportingSerializer(serializers.ModelSerializer):
    instance_id = serializers.CharField(source="provider_alias", read_only=True)
    username = serializers.CharField(source="created_by.username", read_only=True)
    staff_user = serializers.CharField(source="created_by.is_staff", read_only=True)
    provider = serializers.CharField(source='created_by_identity.provider.location', read_only=True)
    size = serializers.SerializerMethodField()
    image_name = serializers.SerializerMethodField()
    version_name = serializers.SerializerMethodField()
    is_featured_image = serializers.SerializerMethodField()
    start_date = serializers.SerializerMethodField()
    end_date = serializers.SerializerMethodField()
    hit_aborted = serializers.SerializerMethodField()
    hit_active = serializers.SerializerMethodField()
    hit_deploy_error = serializers.SerializerMethodField()
    hit_error = serializers.SerializerMethodField()
    hit_active_or_aborted = serializers.SerializerMethodField()
    hit_active_or_aborted_or_error = serializers.SerializerMethodField()

    def get_size(self, obj):
        size = obj.get_size()
        serializer = SizeSummarySerializer(size, context=self.context)
        return serializer.data

    def get_is_featured_image(self, instance):
        try:
            application = self.get_application(instance)
            return application.tags.filter(name__icontains='featured').count() > 0
        except Exception:
            return False

    def get_version_name(self, instance):
        try:
            version = self.get_version(instance)
            return version.name.replace(",", "-")
        except Exception:
            return "N/A"

    def get_image_name(self, instance):
        try:
            application = self.get_application(instance)
            return application.name.replace(",", "-")
        except Exception:
            return "Deleted Image"

    def get_application(self, instance):
        try:
            version = self.get_version(instance)
            return version.application
        except Exception:
            return None

    def get_version(self, instance):
        try:
            return instance.source.providermachine.application_version
        except Exception:
            return None

    def get_end_date(self, instance):
        return instance.end_date.strftime("%x %X") if instance.end_date else None

    def get_start_date(self, instance):
        return instance.start_date.strftime("%x %X")

    def get_hit_active_or_aborted_or_error(self, instance):
        return 1 if (
            self.get_hit_active(instance) or
            self.get_hit_aborted(instance) or
            self.get_hit_error(instance)
        ) else 0

    def get_hit_active_or_aborted(self, instance):
        return 1 if (
            self.get_hit_active(instance) or
            self.get_hit_aborted(instance)
        ) else 0

    def get_hit_aborted(self, instance):
        return (
            not self.get_hit_active(instance) and
            not self.get_hit_deploy_error(instance) and
            not self.get_hit_error(instance)
        )

    def get_hit_active(self, instance):
        return instance.instancestatushistory_set.filter(status__name='active').count() > 0

    def get_hit_deploy_error(self, instance):
        if self.get_hit_active(instance):
            return False
        return instance.instancestatushistory_set.filter(status__name='deploy_error').count() > 0

    def get_hit_error(self, instance):
        if self.get_hit_active(instance):
            return False
        return instance.instancestatushistory_set.filter(status__name='error').count() > 0

    class Meta:
        model = Instance
        fields = (
            'id',
            'instance_id',
            'username',
            'staff_user',
            'provider',
            'image_name',
            'version_name',
            'is_featured_image',
            'hit_aborted',
            'hit_active_or_aborted',
            'hit_active_or_aborted_or_error',
            'hit_active',
            'hit_deploy_error',
            'hit_error',
            'size',
            'start_date',
            'end_date',
        )
