"""
status_type - states which a request transitions through
"""
from django.db import models
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible
import uuid


def get_status_type(status="pending"):
    """
    Fetches a StatusType by the given name

    Creates a new StatusType if a name does not exist
    for the give `status`.
    """
    (status_type, _) = StatusType.objects.get_or_create(name=status)
    return status_type


def get_status_type_id(status="pending"):
    return get_status_type(status=status).id


@python_2_unicode_compatible
class StatusType(models.Model):

    """
    Representation of a State
    """
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=32)
    description = models.CharField(max_length=256, default="", blank=True)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'status_type'
        app_label = 'core'
        unique_together = ("name", "start_date")

    @classmethod
    def default(cls):
        return StatusType(name="pending")

    def __unicode__(self):
        return "%s" % \
            (self.name,)

    def __str__(self):
        return "%s" % \
            (self.name,)
