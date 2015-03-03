"""
status_type - states which a request transitions through
"""
from django.db import models
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible


def get_status_type(status="pending"):
    """
    Fetches a StatusType by the given name

    Creates a new StatusType if a name does not exist
    for the give `status`.
    """
    (status_type, _) = StatusType.objects.get_or_create(name=status)
    return status_type


@python_2_unicode_compatible
class StatusType(models.Model):
    """
    Representation of a State
    """
    name = models.CharField(max_length=32)
    description = models.CharField(max_length=256, default="", blank=True)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'status_type'
        app_label = 'core'

    @classmethod
    def default(cls):
        return StatusType(name="pending")

    def __str__(self):
        return self.name
