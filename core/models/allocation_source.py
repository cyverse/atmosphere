from django.conf import settings
from django.db import models
from django.utils import timezone


class AllocationSource(models.Model):
    name = models.CharField(max_length=255)
    source_id = models.CharField(max_length=255)
    compute_allowed = models.IntegerField()

    # The remaining fields will be 'derived' or 'materialized' from a separate view of the 'events' class
    @property
    def compute_used(self):
        """
        1. Filter down the EventTable to the *user* who matches agg_id and order by _pk_
        2. start 'reading' the stream from the beginning.
        3. Feed this into the engine
        4. Return the result
        Working of this as ref: http://romscodecorner.blogspot.com/2015/02/experimenting-with-event-sourcing-3.html
        and https://github.com/rtouze/event_sourcing_example
        """
        return None

    @property
    def compute_remaining(self):
        return None
    @property
    def global_burn_rate(self):
        return None
    @property
    def time_to_zero(self):
        return None

    def user_burn_rate(self, username):
        return None

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
