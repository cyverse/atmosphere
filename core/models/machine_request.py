"""
  Machine models for atmosphere.
"""
from hashlib import md5

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


from atmosphere.logger import logger

from core.models.script import Package
from core.models.provider import Provider
from core.models.tag import Tag, updateTags
from core.models.identity import Identity
    
class MachineRequest(models.Model):
    """
    Provides information for the MachineRequestThread to start/restart the Queue
    Provides a Parent-Child relationship between the new image and ancestor(s)
    """
    # The instance to image.
    instance = models.ForeignKey("Instance")

    # Machine imaging Metadata
    status = models.CharField(max_length=256)
    parent_machine = models.ForeignKey("ProviderMachine", related_name="ancestor_machine")
    # Specifics for machine imaging.
    iplant_sys_files = models.TextField(default='', blank=True)
    installed_software = models.TextField(default='', blank=True)
    exclude_files = models.TextField(default='', blank=True)
    access_list = models.TextField(default='', blank=True)

    # Data for the new machine.
    new_machine_provider = models.ForeignKey(Provider)
    new_machine_name = models.CharField(max_length=256)
    new_machine_owner = models.ForeignKey(User)
    new_machine_visibility = models.CharField(max_length=256)
    new_machine_description = models.TextField(default='', blank=True)
    new_machine_tags = models.TextField(default='', blank=True)
    #Date time stamps
    start_date = models.DateTimeField(default=timezone.now())
    end_date = models.DateTimeField(null=True, blank=True)

    # Filled in when completed.
    new_machine  = models.ForeignKey("ProviderMachine", null=True, blank=True, related_name="created_machine")
    class Meta:
        db_table = "machine_request"
        app_label = "core"

class MachineExport(models.Model): 
    # The instance to export 
    instance = models.ForeignKey("Instance") 
    # Request related metadata 
    status = models.CharField(max_length=256) 
    #The exported image 
    export_owner = models.ForeignKey(User) 
    export_format = models.CharField(max_length=256) 
    export_file = models.CharField(max_length=256, null=True, blank=True)
    #Request start to image exported 
    start_date = models.DateTimeField(default=timezone.now()) 
    end_date = models.DateTimeField(null=True, blank=True) 
    class Meta:
        db_table = "machine_export"
        app_label = "core"
