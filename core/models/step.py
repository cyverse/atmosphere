from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

from core.models.identity import Identity
from core.models.instance import Instance


class Step(models.Model):
    """
    A step is an atomic unit of workflow in Atmosphere.
    """
    alias = models.CharField(max_length=36) # Typically a uuid.
    name = models.CharField(max_length=1024, blank=True)
    script = models.TextField()
    exit_code = models.IntegerField(null=True, blank=True)
    instance = models.ForeignKey(Instance, null=True, blank=True)
    created_by = models.ForeignKey(User)
    created_by_identity = models.ForeignKey(Identity, null=True)
    start_date = models.DateTimeField(default=timezone.now())
    end_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "step"
        app_label = "core"

    def __unicode__(self):
        return "alias=%s (id=%s|name=%s) exit_code=%s\
        \n%s\ncreated_by=%s identity=%s\n\
        start_date: %s end_date: %s" % (
            self.alias,
            self.id,
            self.name,
            self.exit_code,
            self.script,
            self.created_by,
            self.created_by_identity,
            self.start_date,
            self.end_date)
