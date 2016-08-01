"""
  Instance status history model for atmosphere.
"""
from uuid import uuid4
from datetime import timedelta

from django.db import models, transaction, DatabaseError
from django.db.models import ObjectDoesNotExist
from django.utils import timezone

from threepio import logger


class InstanceStatus(models.Model):

    """
    Used to enumerate the types of actions
    (I.e. Stopped, Suspended, Active, Deleted)
    """
    name = models.CharField(max_length=128)

    def __unicode__(self):
        return "%s" % self.name

    class Meta:
        db_table = "instance_status"
        app_label = "core"


class InstanceStatusHistory(models.Model):

    """
    Used to keep track of each change in instance status
    (Useful for time management)
    """
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    instance = models.ForeignKey("Instance")
    size = models.ForeignKey("Size", null=True, blank=True)
    status = models.ForeignKey(InstanceStatus)
    activity = models.CharField(max_length=36, null=True, blank=True)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)

    def get_total_hours(self):
        from service.monitoring import _get_allocation_result
        identity = self.instance.created_by_identity
        history_list = self.__class__.objects.filter(id=self.id)
        limit_history = [hist.id for hist in history_list]
        limit_instances = [self.instance.provider_alias]
        result = _get_allocation_result(
            identity,
            limit_instances=limit_instances,
            limit_history=limit_history)
        total_hours = result.total_runtime().total_seconds()/3600.0
        hours = round(total_hours, 2)
        return hours

    def previous(self):
        """
        Given that you are a node on a linked-list, traverse yourself backwards
        """
        if self.instance.start_date == self.start_date:
            raise LookupError("This is the first state of instance %s" % self.instance)
        try:
            history = self.instance.instancestatushistory_set.get(start_date=self.end_date)
            if history.id == self.id:
                raise ValueError("There was no matching transaction for Instance:%s end-date:%s" % (self.instance, self.end_date))
        except ObjectDoesNotExist:
            raise ValueError("There was no matching transaction for Instance:%s end-date:%s" % (self.instance, self.end_date))

    def next(self):
        """
        Given that you are a node on a linked-list, traverse yourself forwards
        """
        # In this situation, the instance is presumably still running.
        if not self.end_date:
            if self.instance.end_date:
                raise ValueError("Whoa! The instance %s has been terminated, but status %s has not! This could leak time" % (self.instance,self))
            raise LookupError("This is the final state of instance %s" % self.instance)
        # In this situation, the end_date of the final history is an exact match to the instance's end-date.
        if self.instance.end_date == self.end_date:
            raise LookupError("This is the final state of instance %s" % self.instance)
        # In this situation, the end_date of the final history is "a little off" from the instance's end-date.
        if self == self.instance.get_last_history():
            raise LookupError("This is the final state of instance %s" % self.instance)
        try:
            return self.instance.instancestatushistory_set.get(start_date=self.end_date)
        except ObjectDoesNotExist:
            raise ValueError("There was no matching transaction for Instance:%s end-date:%s" % (self.instance, self.end_date))

    @classmethod
    def transaction(cls, status_name, activity, instance, size,
                    start_time=None, last_history=None):
        try:
            with transaction.atomic():
                if not last_history:
                    # Required to prevent race conditions.
                    last_history = instance.get_last_history()\
                                           .select_for_update(nowait=True)
                    if not last_history:
                        raise ValueError(
                            "A previous history is required "
                            "to perform a transaction. Instance:%s" %
                            (instance,))
                    elif last_history.end_date:
                        raise ValueError("Old history already has end date: %s"
                                         % last_history)
                last_history.end_date = start_time
                last_history.save()
                new_history = InstanceStatusHistory.create_history(
                    status_name, instance, size, start_date=start_time, activity=activity)
                logger.info(
                    "Status Update - User:%s Instance:%s "
                    "Old:%s New:%s Time:%s" %
                    (instance.created_by,
                     instance.provider_alias,
                     last_history.status.name,
                     new_history.status.name,
                     new_history.start_date))
                new_history.save()
            return new_history
        except DatabaseError:
            logger.exception(
                "instance_status_history: Lock is already acquired by"
                "another transaction.")

    @classmethod
    def create_history(cls, status_name, instance, size,
                       start_date=None, end_date=None, activity=None):
        """
        Creates a new (Unsaved!) InstanceStatusHistory
        """
        status, _ = InstanceStatus.objects.get_or_create(name=status_name)
        new_history = InstanceStatusHistory(
            instance=instance, size=size, status=status, activity=activity)
        if start_date:
            new_history.start_date = start_date
            logger.debug("Created new history object: %s " % (new_history))
        if end_date and not new_history.end_date:
            new_history.end_date = end_date
            logger.debug("End-dated new history object: %s " % (new_history))
        return new_history

    def get_active_time(self, earliest_time=None, latest_time=None):
        """
        A set of filters used to determine the amount of 'active time'
        earliest_time and latest_time are taken into account, if provided.
        """

        # When to start counting
        if earliest_time and self.start_date <= earliest_time:
            start_time = earliest_time
        else:
            start_time = self.start_date

        # When to stop counting.. Some history may have no end date!
        if latest_time:
            if not self.end_date or self.end_date >= latest_time:
                final_time = latest_time
                # TODO: Possibly check latest_time < timezone.now() to prevent
                #      bad input?
            else:
                final_time = self.end_date
        elif self.end_date:
            # Final time is end date, because NOW is being used
            # as the 'counter'
            final_time = self.end_date
        else:
            # This is the current status, so stop counting now..
            final_time = timezone.now()

        # Sanity checks are important.
        # Inactive states are not counted against you.
        if not self.is_active():
            return (timedelta(), start_time, final_time)
        if self.start_date > final_time:
            return (timedelta(), start_time, final_time)
        # Active time is easy now!
        active_time = final_time - start_time
        return (active_time, start_time, final_time)

    @classmethod
    def intervals(cls, instance, start_date=None, end_date=None):
        all_history = cls.objects.filter(instance=instance)
        if start_date and end_date:
            all_history = all_history.filter(
                start_date__range=[
                    start_date,
                    end_date])
        elif start_date:
            all_history = all_history.filter(start_date__gt=start_date)
        elif end_date:
            all_history = all_history.filter(end_date__lt=end_date)
        return all_history

    def __unicode__(self):
        return "%s (FROM:%s TO:%s)" % (self.status,
                                       self.start_date,
                                       self.end_date if self.end_date else '')

    def is_active(self):
        """
        Use this function to determine whether or not a specific instance
        status history should be considered 'active'
        """
        if self.status.name == 'active':
            return True
        else:
            return False

    class Meta:
        db_table = "instance_status_history"
        app_label = "core"
