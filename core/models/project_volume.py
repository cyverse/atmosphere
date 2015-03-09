from django.db import models
from core.models.volume import Volume
from core.models.project import Project


class ProjectVolume(models.Model):
    project = models.ForeignKey(Project)
    volume = models.ForeignKey(Volume)

    class Meta:
        db_table = 'project_volumes'
