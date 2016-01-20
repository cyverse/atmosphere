from django.db import models
from core.models.application import Application
from core.models.project import Project


class ProjectApplication(models.Model):
    project = models.ForeignKey(Project)
    application = models.ForeignKey(Application)

    class Meta:
        db_table = 'project_applications'
        managed = False
