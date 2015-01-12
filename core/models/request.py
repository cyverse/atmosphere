"""
requests  - tracks requests
"""
from uuid import uuid4

from django.db import models
from django.utils import timezone

from core.models import Allocation, AtmosphereUser as User, \
    IdentityMembership, Quota


def get_status_type(status="pending"):
    (status_type, _) = StatusType.objects.get_or_create(name=status)
    return status_type


class StatusType(models.Model):
    name = models.CharField(max_length=32)
    description = models.CharField(max_length=256, default="", blank=True)
    start_date = models.DateTimeField(default=timezone.now())
    end_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'status_type'
        app_label = 'core'

    @classmethod
    def default(cls):
        return StatusType(name="pending")


class BaseRequestMixin(models.Model):
    uuid = models.CharField(max_length=36, default=uuid4)
    description = models.CharField(max_length=1024, default="", blank=True)
    status = models.ForeignKey(StatusType)

    # Associated creator and identity
    created_by = models.ForeignKey(User)
    membership = models.ForeignKey(IdentityMembership)

    admin_message = models.CharField(max_length=1024, default="")

    # Request Timeline
    start_date = models.DateTimeField(default=timezone.now())
    end_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    @classmethod
    def is_active(cls, provider, user):
        """
        Returns whether or not the resource request is currently active for the
        given user and provider
        """
        status = StatusType.default()
        return cls.objects.filter(
            user=user, provider=provider, status=status).count() > 0


class AllocationRequest(BaseRequestMixin):
    """
    """
    # Resources requested
    current_allocation = models.ForeignKey(
        Allocation, related_name="current_allocation")
    allocation_requested_text = models.TextField()
    allocation_recieved = models.ForeignKey(
        Allocation, null=True, blank=True, related_name="allocation_recieved")

    class Meta:
        db_table = "allocation_request"
        app_label = "core"


class QuotaRequest(BaseRequestMixin):
    """
    """
    # Resources requested
    current_quota = models.ForeignKey(Quota, related_name="current_quota")
    quota_requested_text = models.TextField()
    quota_recieved = models.ForeignKey(
        Quota, null=True, blank=True, related_name="quota_recieved")

    class Meta:
        db_table = "quota_request"
        app_label = "core"
