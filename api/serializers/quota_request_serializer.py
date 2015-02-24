from core.models import Quota
from core.models.request import QuotaRequest
from core.models.status_type import StatusType
from core.models.user import AtmosphereUser
from rest_framework import serializers


class QuotaRequestSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True, source="uuid", required=False)
    created_by = serializers.SlugRelatedField(
        slug_field='username',
        queryset=AtmosphereUser.objects.all())
    status = serializers.SlugRelatedField(
        slug_field='name',
        queryset=StatusType.objects.all())

    class Meta:
        model = QuotaRequest
        exclude = ('uuid', 'membership')


class ResolveQuotaRequestSerializer(serializers.ModelSerializer):
    status = serializers.SlugRelatedField(
        slug_field='name',
        queryset=StatusType.objects.all())

    created_by = serializers.SlugRelatedField(
        slug_field='username',
        queryset=AtmosphereUser.objects.all())

    quota = serializers.SlugRelatedField(
        slug_field='id',
        queryset=Quota.objects.all())

    class Meta:
        model = QuotaRequest
        exclude = ('uuid', 'membership')
