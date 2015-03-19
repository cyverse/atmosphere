from django.db import models
from core.models.instance import Instance
from core.models.project import Project


class ProjectInstance(models.Model):
    project = models.ForeignKey(Project)
    instance = models.ForeignKey(Instance)

    class Meta:
        db_table = 'project_instances'
        managed = False
