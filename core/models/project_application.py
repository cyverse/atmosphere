from django.db import models
from core.models.application import Application
from core.models.project import Project


class ProjectApplication(models.Model):
    project = models.ForeignKey(Project)
    application = models.ForeignKey(Application)

    def __unicode__(self):
        return "%s: %s - %s" %\
            (self.id, unicode(self.project), self.application)

    class Meta:
        db_table = 'project_applications'
        managed = False
