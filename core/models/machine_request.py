"""
  Machine models for atmosphere.
"""

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


from core.models.provider import Provider
from core.models.machine import createProviderMachine


class MachineRequest(models.Model):
    """
    Storage container for the MachineRequestThread to start/restart the Queue
    Provides a Parent-Child relationship between the new image and ancestor(s)
    """
    # The instance to image.
    instance = models.ForeignKey("Instance")

    # Machine imaging Metadata
    status = models.CharField(max_length=256)
    parent_machine = models.ForeignKey("ProviderMachine",
                                       related_name="ancestor_machine")
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
    new_machine = models.ForeignKey("ProviderMachine",
                                    null=True, blank=True,
                                    related_name="created_machine")
    def new_machine_is_public(self):
        """
        Return True if public, False if private
        """
        return self.new_machine_visibility == 'public'

    def __unicode__(self):
        return '%s Instance: %s Name: %s Status: %s'\
                % (self.new_machine_owner, self.instance.provider_alias,
                   self.new_machine_name, self.status)

    class Meta:
        db_table = "machine_request"
        app_label = "core"


def process_machine_request(machine_request, new_image_id):
    from core.models.tag import Tag
    #Build the new provider-machine object and associate
    new_machine = createProviderMachine(
        machine_request.new_machine_name, new_image_id,
        machine_request.new_machine_provider_id)
    generic_mach = new_machine.machine
    tags = [Tag.objects.get(name__iexact=tag) for tag in
            machine_request.new_machine_tags.split(',')] \
        if machine_request.new_machine_tags else []
    generic_mach.tags = tags
    generic_mach.description = machine_request.new_machine_description
    generic_mach.save()
    machine_request.new_machine = new_machine
    machine_request.end_date = timezone.now()
    machine_request.status = 'completed'
    machine_request.save()
    return machine_request


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
