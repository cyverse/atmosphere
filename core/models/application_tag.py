from django.db import models
from core.models.application import Application
from core.models.tag import Tag


class ApplicationTag(models.Model):
    application = models.ForeignKey(Application)
    tag = models.ForeignKey(Tag)

    def __unicode__(self):
        return "%s: %s - %s" %\
            (self.id, self.application, self.tag)

    class Meta:
        db_table = 'application_tags'
        managed = False
