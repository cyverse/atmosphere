"""
  Abstract models for atmosphere. 
  NOTE: These models should NEVER be created directly. 
  See the respective sub-classes for complete implementation details.
"""
from django.db import models
from django.utils import timezone
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
