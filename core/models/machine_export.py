from django.db import models
from django.utils import timezone
from core.models.user import AtmosphereUser as User

class MachineExport(models.Model):
    # The instance to export
    instance = models.ForeignKey("Instance")
    # Request related metadata
    status = models.CharField(max_length=256)
    #The exported image
    export_name = models.CharField(max_length=256)
    export_owner = models.ForeignKey(User)
    export_format = models.CharField(max_length=256)
    export_file = models.CharField(max_length=256, null=True, blank=True)
    #Request start to image exported
    start_date = models.DateTimeField(default=timezone.now())
    end_date = models.DateTimeField(null=True, blank=True)
    #TODO: Perhaps a field for the MD5 Hash?

    def __unicode__(self):
        return '%s Instance export of: %s Status:%s'\
                % (self.export_owner,
                   self.instance.provider_alias,
                   self.status)

    class Meta:
        db_table = "machine_export"
        app_label = "core"

def process_machine_export(machine_export, *args, **kwargs):
    if kwargs.get('url'):
        machine_export.export_file = 'S3://%s ' % kwargs['url']
    machine_export.status = 'Completed'
    machine_export.end_date = timezone.now()
    machine_export.save()
    """
    This function will define all the operations that should
    occur after a successful machine export (see service/)
    """
