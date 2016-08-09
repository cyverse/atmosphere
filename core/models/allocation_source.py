from django.conf import settings
from django.db import models
from django.utils import timezone
from threepio import logger
from pprint import pprint

class AllocationSource(models.Model):
    name = models.CharField(max_length=255)
    source_id = models.CharField(max_length=255)
    compute_allowed = models.IntegerField()

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
    # Possible FIXME: Should this point to FK-UserAllocationSource? Add these fields to FK-UserAllocationSource?
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

def total_usage(username, start_date, allocation_source=None,end_date=None, burn_rate=False):
    """ 
        This function outputs the total allocation usage in hours
    """
    from service.allocation_logic import create_report
    if not end_date:
        end_date = timezone.now()
    logger.info("Calculating total usage for User %s with AllocationSource %s from %s-%s" % (username, allocation_source, start_date, end_date))
    user_allocation = create_report(start_date,end_date,user_id=username,allocation_source=allocation_source)
    total_allocation = 0.0
    for data in user_allocation:
        total_allocation += data['applicable_duration']
    if burn_rate:
        burn_rate_total = 0 if len(user_allocation)<1 else user_allocation[-1]['burn_rate']
        return [round(total_allocation/3600.0,2),burn_rate_total]
    return round(total_allocation/3600.0,2)
