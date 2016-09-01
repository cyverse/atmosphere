from django.db import models
from core.models.link import ExternalLink
from core.models.project import Project


class ProjectExternalLink(models.Model):
    project = models.ForeignKey(Project)
    externallink = models.ForeignKey(ExternalLink)

    def __unicode__(self):
        return "%s: %s - %s" %\
            (self.id, unicode(self.project), self.externallink)

    class Meta:
        db_table = 'project_links'
        managed = False
