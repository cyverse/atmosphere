"""
  Abstract models for atmosphere. 
  NOTE: These models should NEVER be created directly. 
  See the respective sub-classes for complete implementation details.
"""
from uuid import uuid4

from django.db import models
from django.db.models import Q
from django.utils import timezone

from core.query import only_current
from core.models.group import IdentityMembership
from core.models.identity import Identity
from core.models.provider import Provider
from core.models.status_type import StatusType
from core.models.user import AtmosphereUser as User


class BaseRequest(models.Model):
    """
    Base model which represents a request object
    """
    uuid = models.CharField(max_length=36, default=uuid4)
    request = models.TextField()
    description = models.CharField(max_length=1024, default="", blank=True)
    status = models.ForeignKey(StatusType)

    # Associated creator and identity
    created_by = models.ForeignKey(User)
    membership = models.ForeignKey(IdentityMembership)

    admin_message = models.CharField(max_length=1024, default="", blank=True)

    # Request Timeline
    start_date = models.DateTimeField(default=timezone.now)
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


class BaseHistory(models.Model):
    """
    Base model which is used to track changes in another model
    """
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETED"

    OPERATIONS = (
        (CREATE, "The field has been created."),
        (UPDATE, "The field has been updated."),
        (DELETE, "The field has been deleted."),
    )

    field_name = models.CharField(max_length=255)
    operation = models.CharField(max_length=255,
                                 choices=OPERATIONS, default=UPDATE)
    new_value = models.TextField()
    previous_value = models.TextField()
    created_on = models.DateTimeField(default=timezone.now())

    class Meta:
        abstract = True
