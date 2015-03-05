from uuid import uuid4
from django.db import models
from django.utils import timezone
from core.models.application import Application
from core.models.instance import Instance
from core.models.group import Group
from core.models.volume import Volume

from threepio import logger


class Project(models.Model):
    """
    A Project is an abstract container of (0-to-many):
      * Application
      * Instance
      * Volume
    """
    uuid = models.CharField(max_length=36, unique=True, default=uuid4)
    name = models.CharField(max_length=256)
    description = models.TextField(blank=True)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    owner = models.ForeignKey(Group, related_name="projects")
    applications = models.ManyToManyField(Application, related_name="projects",
                                          null=True, blank=True)
    instances = models.ManyToManyField(Instance, related_name="projects",
                                       null=True, blank=True, through='ProjectInstance')
    volumes = models.ManyToManyField(Volume, related_name="projects",
                                     null=True, blank=True, through='ProjectVolume')

    def __unicode__(self):
        return "%s Owner:%s: Apps:%s Instances:%s Volumes:%s"\
            % (self.name, self.owner,
               self.applications.all(), self.instances.all(),
               self.volumes.all())

    def has_running_resources(self):
        now_date = timezone.now()
        if any(not instance.end_date or instance.end_date >= now_date
               for instance in self.instances.all()):
            return True
        if any(not volume.end_date or volume.end_date >= now_date
               for volume in self.volumes.all()):
            return True

    def remove_object(self, related_obj):
        """
        Use this function to move A single object
        to Project X
        """
        return related_obj.projects.remove(self)

    def add_object(self, related_obj):
        """
        Use this function to move A single object
        to Project X
        """
        self._test_project_ownership(related_obj)
        return related_obj.projects.add(self)

    def _test_project_ownership(self, related_obj):
        user = related_obj.created_by
        group = self.owner
        if user in group.user_set.all():
            return True
        raise Exception("CANNOT add Resource:%s User:%s does NOT belong to Group:%s"
                        % (related_obj, user, group))
        
    def copy_objects(self, to_project):
        """
        Use this function to move ALL objects
        from Project X to Project Y
        """
        [to_project.add_object(app) for app in self.applications.all()]
        [to_project.add_object(inst) for inst in self.instances.all()]
        [to_project.add_object(vol) for vol in self.volumes.all()]

    def delete_project(self):
        """
        Use this function to remove Project X
        from all objects using it before removing
        the entire Project
        """
        [self.remove_object(app) for app in self.applications.all()]
        [self.remove_object(inst) for inst in self.instances.all()]
        [self.remove_object(vol) for vol in self.volumes.all()]
        self.end_date = timezone.now()
        self.save()

    class Meta:
        db_table = 'project'
        app_label = 'core'
