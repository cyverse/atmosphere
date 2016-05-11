from django.db import models
from core.models.instance import Instance
from core.models.tag import Tag


class InstanceTag(models.Model):
    instance = models.ForeignKey(Instance)
    tag = models.ForeignKey(Tag)

    class Meta:
        db_table = 'instance_tags'
        managed = False

    def __unicode__(self):
        return "%s - %s" % (self.instance, self.tag)
