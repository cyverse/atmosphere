from django.db import models
from core.models.volume import Volume
from core.models.project import Project


class ProjectVolume(models.Model):
    project = models.ForeignKey(Project)
    volume = models.ForeignKey(Volume)

    def __unicode__(self):
        return "%s: %s - %s" %\
            (self.id, unicode(self.project), self.volume)

    class Meta:
        db_table = 'project_volumes'
        managed = False
