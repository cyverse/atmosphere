from decimal import Decimal

import django
from rest_framework import serializers

from core.models.allocation_source import AllocationSource, AllocationSourceSnapshot, UserAllocationSnapshot
from core.models.user import AtmosphereUser
from core.models.event_table import EventTable
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class AllocationSourceSerializer(serializers.HyperlinkedModelSerializer):
    compute_allowed = serializers.SerializerMethodField()
    compute_used = serializers.SerializerMethodField()
    global_burn_rate = serializers.SerializerMethodField()
    user_burn_rate = serializers.SerializerMethodField()
    user_compute_used = serializers.SerializerMethodField()
    user_snapshot_updated = serializers.SerializerMethodField()
    updated = serializers.SerializerMethodField()
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:allocationsource-detail',
    )

    def _get_allocation_source_snapshot(self, allocation_source, attr_name):
        snapshot = AllocationSourceSnapshot.objects.filter(
            allocation_source=allocation_source).first()
        if not snapshot:
            return None
        attr = getattr(snapshot, attr_name)
        return attr

    def _get_request_user(self):
        if 'request' not in self.context:
            raise ValueError("Expected 'request' context for this serializer")
        return self.context['request'].user

    def _get_user_allocation_snapshot(self, allocation_source, attr_name):
        user = self._get_request_user()
        snapshot = UserAllocationSnapshot.objects.filter(
            allocation_source=allocation_source, user=user).first()
        if not snapshot:
            return None
        attr = getattr(snapshot, attr_name)
        return attr

    def get_global_burn_rate(self, allocation_source):
        special_allocation_sources = getattr(django.conf.settings, 'SPECIAL_ALLOCATION_SOURCES', {})
        if allocation_source.name in special_allocation_sources:
            return self.get_user_burn_rate(allocation_source)
        else:
            return self._get_allocation_source_snapshot(allocation_source, 'global_burn_rate')

    def get_user_snapshot_updated(self, allocation_source):
        return self._get_user_allocation_snapshot(allocation_source, 'updated')

    def get_user_burn_rate(self, allocation_source):
        return self._get_user_allocation_snapshot(allocation_source, 'burn_rate')

    def get_user_compute_used(self, allocation_source):
        return self._get_user_allocation_snapshot(allocation_source, 'compute_used') or Decimal(0.000)

    def get_compute_used(self, allocation_source):
        """
        Return last known value of AllocationSourceSnapshot in hrs
        """
        assert isinstance(allocation_source, AllocationSource)
        special_allocation_sources = getattr(django.conf.settings, 'SPECIAL_ALLOCATION_SOURCES', {})
        if allocation_source.name in special_allocation_sources:
            return self.get_user_compute_used(allocation_source)
        else:
            return self._get_allocation_source_snapshot(allocation_source, 'compute_used')

    def get_compute_allowed(self, allocation_source):
        assert isinstance(allocation_source, AllocationSource)
        special_allocation_sources = getattr(django.conf.settings, 'SPECIAL_ALLOCATION_SOURCES', {})
        if allocation_source.name in special_allocation_sources:
            sub_allocation_compute_allowed = special_allocation_sources[allocation_source.name]['compute_allowed']
            return sub_allocation_compute_allowed
        else:
            return allocation_source.compute_allowed

    def get_updated(self, allocation_source):
        return self._get_allocation_source_snapshot(allocation_source, 'updated')

    class Meta:
        model = AllocationSource
        fields = (
            'id', 'url', 'name', 'uuid', 'compute_allowed', 'start_date',
            'end_date', 'compute_used', 'global_burn_rate', 'updated', 'uuid', 'renewal_strategy',
            'user_compute_used', 'user_burn_rate', 'user_snapshot_updated')
