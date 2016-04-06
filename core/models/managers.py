"""
This special file is for keeping track of `models.Manager` classes.
TODO:
  If this file grows too large to maintain,
  create a `managers` folder and split out
  files based on class being managed.
"""
from core.query import only_current_instances
from django.db import models
from django.utils import timezone


class InstanceActionsManager(models.Manager):

    def get_queryset(self):
        # Ignores: Terminate, Imaging
        instance_actions = [
            'Start', 'Stop',
            'Resume', 'Suspend',
            'Shelve', 'Shelve Offload', 'Unshelve',
            'Reboot', 'Hard Reboot',
            'Resize', 'Redeploy'
        ]
        query = models.Q(name__in=instance_actions)
        return super(InstanceActionsManager, self).get_queryset().filter(query)


class ActiveInstancesManager(models.Manager):

    def get_queryset(self):
        now_time = timezone.now()
        return super(
            ActiveInstancesManager,
            self) .get_queryset().filter(only_current_instances(now_time))

