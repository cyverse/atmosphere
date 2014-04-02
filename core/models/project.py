from django.db import models
from django.utils import timezone

from core.models.application import Application
from core.models.instance import Instance
from core.models.user import AtmosphereUser
from core.models.volume import Volume

from threepio import logger


class Project(models.Model):
    """
    A Project is an abstract container of (0-to-many):
      * Application
      * Instance
      * Volume
    """
    name = models.CharField(max_length=256)
    description = models.TextField()
    owner = models.ForeignKey(AtmosphereUser, related_name="projects")
    applications = models.ManyToManyField(Application, related_name="projects",
                                          null=True, blank=True)
    instances = models.ManyToManyField(Instance, related_name="projects",
                                       null=True, blank=True)
    volumes = models.ManyToManyField(Volume, related_name="projects",
                                     null=True, blank=True)
    def __unicode__(self):
        return "%s Owner:%s: Apps:%s Instances:%s Volumes:%s"\
                % (self.name, self.owner,
                   self.applications.all(), self.instances.all(),
                   self.volumes.all())

    def migrate_objects(self, to_project):
        for app in self.applications.all():
            to_project.applications.add(app)
        for app in self.instances.all():
            to_project.instances.add(app)
        for app in self.volumes.all():
            to_project.volumes.add(app)

    def delete_project(self):
        self.applications.all().delete()
        self.instances.all().delete()
        self.volumes.all().delete()
        self.end_date = timezone.now()
        self.save()

    class Meta:
        db_table = 'project'
        app_label = 'core'

