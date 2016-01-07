from django.db import models
from core.models.link import ExternalLink
from core.models.project import Project


class ProjectExternalLink(models.Model):
    project = models.ForeignKey(Project)
    externallink = models.ForeignKey(ExternalLink)

    class Meta:
        db_table = 'project_links'
        managed = False
