from django.conf import settings
from django.db import models
from django.utils import timezone

class AllocationSource(models.Model):
    name = models.CharField(max_length=255)
    source_id = models.CharField(max_length=255)
    compute_allowed = models.IntegerField()

    # The remaining fields will be 'derived' or 'materialized' from a separate view of the 'events' class
    """
    1. Filter down the EventTable to the *user* who matches agg_id and order by _pk_
    2. start 'reading' the stream from the beginning.
    3. Feed this into the engine
    4. Return the result
    Working of this as ref: http://romscodecorner.blogspot.com/2015/02/experimenting-with-event-sourcing-3.html
    and https://github.com/rtouze/event_sourcing_example
    """

    def __unicode__(self):
        return "%s (ID:%s, Compute Allowed:%s)" %\
            (self.name, self.source_id,
             self.compute_allowed)


    class Meta:
        db_table = 'allocation_source'
        app_label = 'core'

class UserAllocationSource(models.Model):
    """
    This table keeps track of whih allocation sources belong to an AtmosphereUser.

    NOTE: This table is basically a cache so that we do not have to query out to the
    "Allocation Source X" API endpoint each call.
          It is presumed that this table will be *MAINTAINED* regularly via periodic task.
    """

    user = models.ForeignKey("AtmosphereUser")
    allocation_source = models.ForeignKey(AllocationSource)

    def __unicode__(self):
        return "%s (User:%s, AllocationSource:%s)" %\
            (self.id, self.user,
             self.allocation_source)

    class Meta:
        db_table = 'user_allocation_source'
        app_label = 'core'


class UserAllocationBurnRateSnapshot(models.Model):
    """
    Fixme: Potential optimization -- user_allocation_source could just store burn_rate and updated?
    """
    user = models.ForeignKey("AtmosphereUser")
    allocation_source = models.ForeignKey(AllocationSource)
    burn_rate = models.DecimalField(max_digits=19, decimal_places=10)
    updated = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return "Instance %s is using Allocation %s at %s hours/hour (Updated:%s)" %\
            (self.user, self.allocation_source, self.burn_rate, self.updated)

    class Meta:
        db_table = 'user_allocation_burn_rate_snapshot'
        app_label = 'core'
        unique_together = ('user','allocation_source')


class InstanceAllocationSourceSnapshot(models.Model):
    instance = models.OneToOneField("Instance")
    allocation_source = models.ForeignKey(AllocationSource)
    updated = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return "%s is using allocation %s" %\
            (self.instance, self.allocation_source)
    class Meta:
        db_table = 'instance_allocation_source_snapshot'
        app_label = 'core'


class AllocationSourceSnapshot(models.Model):
    allocation_source = models.OneToOneField(AllocationSource)
    updated = models.DateTimeField(auto_now=True)
    # all fields are stored in DecimalField to allow for partial hour calculation
    # of up to approximately one billion with a resolution of 10 decimal places
    global_burn_rate = models.DecimalField(max_digits=19, decimal_places=10)
    compute_used = models.DecimalField(max_digits=19, decimal_places=10)

    def __unicode__(self):
        return "%s (Used:%s, Burn Rate:%s Updated on:%s)" %\
            (self.allocation_source, self.compute_used,
             self.global_burn_rate, self.updated)
    class Meta:
        db_table = 'allocation_source_snapshot'
        app_label = 'core'

