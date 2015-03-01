from django.db import models
from core.models.instance import Instance
from core.models.project import Project


class ProjectInstance(models.Model):
    project = models.ForeignKey(Project, related_name="project")
    instance = models.ForeignKey(Instance, related_name="project")

    class Meta:
        db_table = 'project_instances'
