"""
status_type - states which a request transitions through
"""
from django.db import models
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible
import uuid


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
        unique_together = ("name",)

    def __unicode__(self):
        return "%s" % \
            (self.name,)

    def __str__(self):
        return "%s" % \
            (self.name,)
