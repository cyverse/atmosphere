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


"""
Instance ModelManagers
"""


class ActiveInstancesManager(models.Manager):

    def get_queryset(self):
        now_time = timezone.now()
        return super(
            ActiveInstancesManager,
            self) .get_queryset().filter(only_current_instances(now_time))


"""
EventTable ModelManagers
"""


class PlaybookHistoryManager(models.Manager):

    def get_queryset(self):
        queryset = super(
            PlaybookHistoryManager,
            self).get_queryset()
        return queryset.filter(
            name="instance_playbook_history_updated")
