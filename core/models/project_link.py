from django.db import models
from core.models.link import ExternalLink
from core.models.project import Project


class ProjectExternalLink(models.Model):
    project = models.ForeignKey(Project)
    external_link = models.ForeignKey(ExternalLink)

    class Meta:
        db_table = 'project_externallinks'
        managed = False
