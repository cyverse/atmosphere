from django.db import models
from django.utils import timezone
from django.utils import text
from core.models import AtmosphereUser as User

from core.models.flow import Flow
from core.models.identity import Identity
from core.models.instance import Instance


class Step(models.Model):
    """
    A step is an atomic unit of workflow in Atmosphere.
    """
    alias = models.CharField(max_length=36)  # Typically a uuid.
    name = models.CharField(max_length=1024, blank=True)
    script = models.TextField()
    exit_code = models.IntegerField(null=True, blank=True)
    flow = models.ForeignKey(Flow, null=True, blank=True)
    instance = models.ForeignKey(Instance, null=True, blank=True)
    created_by = models.ForeignKey(User)
    created_by_identity = models.ForeignKey(Identity, null=True)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "step"
        app_label = "core"


    def get_script_name(self):
        return text.slugify(self.name + "_" + self.alias) + ".sh"

    def abbreviate_script(self, max_length=24):
        if self.script:
            return self.script.replace("\n", "")[0:max_length]
        else:
            return self.script

    def __unicode__(self):
        return "alias=%s (id=%s|name=%s) {%s} exit_code=%s flow=%s instance=%s created_by=%s "\
            "identity=%s start_date: %s end_date %s" % (
                self.alias,
                self.id,
                self.name,
                self.abbreviate_script(128),
                self.exit_code,
                self.flow,
                self.instance,
                self.created_by,
                self.created_by_identity,
                self.start_date,
                self.end_date)
