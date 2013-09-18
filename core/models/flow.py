"""
"""
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

from core.models.identity import Identity
from core.models.instance import Instance


class FlowType(models.Model):
    """
    FlowType describes the type of workflow.

    A chain FlowType groups step(s) that are run one after the other.
    A group FlowType groups step(s) that are run in parallel.
    """
    name = models.CharField(max_length=256, blank=True)
    start_date = models.DateTimeField(default=timezone.now())
    end_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "flowtype"
        app_label = "core"

    def __unicode__(self):
        return "(id=%s|name=%s) start_date=%s end_date = %s" % (self.id, self.name, self.start_date, self.end_date)


class Flow(models.Model):
    """
    A group of steps executed similarly.
    """
    alias = models.CharField(max_length=36)  # Typically a uuid.
    name = models.CharField(max_length=1024, blank=True)
    status = models.IntegerField(null=True, blank=True)
    type = models.ForeignKey(FlowType)
    instance = models.ForeignKey(Instance, null=True, blank=True)
    created_by = models.ForeignKey(User)
    created_by_identity = models.ForeignKey(Identity, null=True)
    start_date = models.DateTimeField(default=timezone.now())
    end_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "flow"
        app_label = "core"

    def __unicode__(self):
        return "alias=%s (id=%s|name=%s) status=%s type=%s created_by=%s "\
            "identity=%s start_date: %s end_date %s"\
            % (self.alias,
               self.id,
               self.name,
               self.status,
               self.type,
               self.created_by,
               self.created_by_identity,
               self.start_date,
               self.end_date)
