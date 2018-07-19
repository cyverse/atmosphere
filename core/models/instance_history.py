"""
  Instance status history model for atmosphere.
"""
from time import sleep
from random import random
from uuid import uuid4
from datetime import timedelta
from django.db import models, transaction, IntegrityError
from django.db.models import ObjectDoesNotExist, Q
from django.contrib.postgres.fields import JSONField
from django.utils import timezone
from threepio import logger


class InstanceStatus(models.Model):
    name = models.CharField(max_length=128)

    def __unicode__(self):
        return "%s" % self.name

    class Meta:
        db_table = "instance_status"
        app_label = "core"


class InstanceStatusHistory(models.Model):
    """
    Used to keep track of each change in instance status
    """
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    # It is a misnomer, but PositiveIntegerField does accept 0
    version = models.PositiveIntegerField(default=0)
    instance = models.ForeignKey("Instance")
    size = models.ForeignKey("Size")
    status = models.ForeignKey(InstanceStatus)
    activity = models.CharField(max_length=36, default="", blank=True)
    start_date = models.DateTimeField(default=timezone.now, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    extra = models.TextField(default="", blank=True)

    def is_active(self):
        return self.status.name ==  'active'

    def is_atmo_specific(self):
        return self.status.name in [
            "networking", "deploying", "networking_error", "deploy_error"
        ]

    def __unicode__(self):
        return "{} on {}".format(self.status, self.start_date)

    @classmethod
    def latest_history(clss, core_instance):
        return clss.objects.filter(instance=core_instance) \
            .order_by('start_date') \
            .last()

    @classmethod
    def update_history(clss, *args, **kwargs):
        """
        Given the status name and activity look up the previous history object
        If nothing has changed return (False, last_history), otherwise start
        new history object and return (True, new_history)
        """
        core_instance, status, activity = args
        size = kwargs.get('size', None)
        extra = kwargs.get('extra', None)
        retry_attempts = kwargs.get('retry_attempts', 0)

        now_time = timezone.now()

        last_history = clss.latest_history(core_instance)
        if not last_history:
            assert size, "If the beginning of instance history, a size must be provided (instance: {})".format(
                core_instance.provider_alias)
            first_history = clss.create_history(
                core_instance,
                status,
                activity,
                size,
                start_date=now_time,
                extra=extra,
                version=0)
            return (True, first_history)

        size = size or last_history.size
        if last_history.status.name == status \
                and last_history.activity == activity \
                and last_history.size == size:
            return (False, last_history)

        # Every time a history is created an integrity error can be raised.
        # This happens when two histories are created for the same instance
        # and version. If we catch an integrity error we simply retry.
        try:

            # Ensure the all-or-nothingness of end-dating and creating a new
            # history
            with transaction.atomic():
                last_history.end_date = now_time
                last_history.save()
                new_history = clss.create_history(
                    core_instance,
                    status,
                    activity,
                    size,
                    start_date=now_time,
                    extra=extra,
                    version=last_history.version + 1)

        except IntegrityError as exc:
            # Before retrying, add a bit of delay
            sleep(random())
            return clss.update_history(*args, **kwargs)

        return (True, new_history)

    @classmethod
    def create_history(clss,
                       instance,
                       status_name,
                       activity,
                       size,
                       start_date=None,
                       extra=None,
                       version=None):
        status, _ = InstanceStatus.objects.get_or_create(name=status_name)
        kwargs = {
            "instance": instance,
            "status": status,
            "activity": activity,
            "size": size
        }
        if version is None:
            last_history = InstanceStatusHistory.latest_history(instance)
            version = (last_history and last_history.version + 1) or 0
        kwargs["version"] = version
        if start_date:
            kwargs["start_date"] = start_date
        if extra:
            kwargs["extra"] = extra
        return clss.objects.create(**kwargs)

    class Meta:
        unique_together = ("instance", "version")
        db_table = "instance_status_history"
        app_label = "core"
