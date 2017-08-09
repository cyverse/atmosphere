import uuid

from django.db import models
from django.contrib.postgres.fields import JSONField
from core.models.instance import Instance


class InstancePlaybookSnapshot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, unique=True, editable=False)
    instance = models.ForeignKey(Instance, related_name="playbooks")
    updated = models.DateTimeField(auto_now=True)
    playbook_name = models.CharField(max_length=255)
    playbook_arguments = JSONField()
    status = models.CharField(max_length=255)

    def __unicode__(self):
        return "%s - %s for instance %s: %s" % (
            self.playbook_name, self.playbook_arguments,
            self.instance.provider_alias, self.status)
