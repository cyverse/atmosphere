from django.db import models
from django.utils import timezone
from django.conf import settings
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

    def prepare_manager(self):
        """
        Prepares, but does not initialize, manager(s)
        This allows the manager and required credentials to be passed to celery
        without causing serialization errors
        """
        from chromogenic.drivers.openstack import ImageManager as OSImageManager
        from chromogenic.drivers.eucalyptus import ImageManager as EucaImageManager
        from chromogenic.drivers.virtualbox import ImageManager as VBoxImageManager

        orig_provider = self.instance.provider_machine.provider
        orig_type = orig_provider.get_type_name().lower()
        dest_provider = None
        dest_type = "VirtualBox"

        origCls = destCls = None
        if orig_type == 'eucalyptus':
            origCls = EucaImageManager
        elif orig_type == 'openstack':
            origCls = OSImageManager

        if dest_type == orig_type:
            destCls = origCls
        elif dest_type == 'eucalyptus':
            destCls = EucaImageManager
        elif dest_type == 'openstack':
            destCls = OSImageManager
        elif dest_type == 'VirtualBox':
            destCls = VBoxImageManager

        orig_creds, dest_creds = self.get_credentials()
        orig_creds = origCls._build_image_creds(orig_creds)
        dest_creds = {
                #For exporting the image
                'image_id':self.instance.provider_machine.identifier,
                #For exporting the instance
                'instance_id':self.instance.provider_alias,
                'image_name':self.export_name,
                'format_type':self.export_format,
                'clean_image':True,
                'keep_image':True,
                #TODO: Upload if selected by user ( Temporary ?)
                'upload':False,
                'download_dir':settings.LOCAL_STORAGE,
                #TODO: Add support, or remove
                #'snapshot_id':self.snapshot_id,
                'snapshot_id':None,
                }

        return (origCls, orig_creds, destCls, dest_creds)

    def get_credentials(self):
        old_provider = self.instance.provider_machine.provider
        old_creds = old_provider.get_credentials()
        old_admin = old_provider.get_admin_identity().get_credentials()
        old_creds.update(old_admin)
        # TODO: Probably not necessary, just send the same copy
        new_creds = old_creds.copy()
        return (old_creds, new_creds)

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
