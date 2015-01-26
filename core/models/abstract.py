"""
  Abstract models for atmosphere. 
  NOTE: These models should NEVER be created directly. 
  See the respective sub-classes for complete implementation details.
"""
from django.db import models
from django.db.models import Q
from django.utils import timezone
from core.query import only_current
from core.models.provider import Provider
from core.models.identity import Identity
from core.models.user import AtmosphereUser

class InstanceSource(models.Model):
    """
    An InstanceSource can be:
    * A bootable volume 
    * A snapshot of a previous/existing Instance
    * A ProviderMachine/Application
    """
    esh = None
    provider = models.ForeignKey(Provider)
    identifier = models.CharField(max_length=256)
    created_by = models.ForeignKey(AtmosphereUser, blank=True, null=True,
            related_name="source_set")
    created_by_identity = models.ForeignKey(Identity, blank=True, null=True)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)

    @classmethod
    def _current_source_query_args(cls):
        now_time = timezone.now()
        query_args = (
                #1. Provider non-end-dated
                Q(provider__end_date=None)
                | Q(provider__end_date__gt=now_time),
                #2. Source non-end-dated
                only_current(now_time),
                #3. (Seperately) Provider is active
                Q(provider__active=True))
        return query_args
    @classmethod
    def current_sources(cls):
        """
        Return a list that contains sources that match ALL criteria:
        1. NOT End dated (Or end dated later than NOW)
        2. Provider is Active
        3. Provider NOT End dated (Or end dated later than NOW)
        """
        now_time = timezone.now()
        return InstanceSource.objects.filter(
                *InstanceSource._current_source_query_args())
        #return InstanceSource.objects.filter(
        #    Q(provider__end_date=None)
        #    | Q(provider__end_date__gt=now_time),
        #    only_current(now_time), provider__active=True)

    #Useful for querying/decision making w/o a Try/Except
    def is_volume(self):
        try:
            volume = self.volume
            return True
        except Exception, not_volume:
            return False

    def is_machine(self):
        try:
            machine = self.providermachine
            return True
        except Exception, not_machine:
            return False

    #Useful for the admin fields
    def source_end_date(self):
        raise NotImplementedError("Implement this in the sub-class")
    def source_provider(self):
        raise NotImplementedError("Implement this in the sub-class")
    def source_identifier(self):
        raise NotImplementedError("Implement this in the sub-class")
    class Meta:
        db_table = "instance_source"
        app_label = "core"
        unique_together = ('provider', 'identifier')
