import os

from django.db import models
from django.utils import timezone
from django.conf import settings
from core.models.user import AtmosphereUser as User

from chromogenic.drivers.openstack import ImageManager as OSImageManager
from chromogenic.drivers.eucalyptus import ImageManager as EucaImageManager


class ExportRequest(models.Model):
    # The machine to export
    source = models.ForeignKey("InstanceSource")
    # Request related metadata
    status = models.CharField(max_length=256)
    # The exported image
    export_name = models.CharField(max_length=256)
    export_owner = models.ForeignKey(User)
    export_format = models.CharField(max_length=256)
    export_file = models.CharField(max_length=256, null=True, blank=True)
    # Request start to image exported
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    # TODO: Perhaps a field for the MD5 Hash?

    def complete_export(self, export_file_path):
        self.status = 'completed'
        self.export_file = export_file_path
        self.end_date = timezone.now()
        self.save()

    def get_admin_provider(self):
        return self.source.provider

    def get_admin_driver(self):
        from service import driver
        old_provider = self.get_admin_provider()
        admin_driver = driver.get_admin_driver(old_provider)
        return admin_driver

    def get_credentials(self):
        prov = self.get_admin_provider()
        creds = prov.get_credentials()
        admin_creds = prov.get_admin_identity().get_credentials()
        creds.update(admin_creds)
        return creds

    def _extract_os_file_location(self, download_dir):
        # Openstack snapshots are saved as a QCOW2
        ext = "qcow2"
        download_location = os.path.join(
            download_dir,
            self.export_owner.username)
        download_location = os.path.join(
            download_location, '%s.%s' %
            (self.export_name, ext))
        return download_location

    def prepare_manager(self):
        """
        Prepares, but does not initialize, manager(s)
        This allows the manager and required credentials to be passed to celery
        without causing serialization errors
        """
        orig_provider = self.source.provider
        orig_type = orig_provider.get_type_name().lower()

        origCls = None
        if orig_type == 'eucalyptus':
            origCls = EucaImageManager
        elif orig_type == 'openstack':
            origCls = OSImageManager

        all_creds = self.get_credentials()
        image_creds = origCls._build_image_creds(all_creds)
        return (origCls, image_creds)

    def get_export_args(self):
        default_kwargs = {
            'image_name': self.export_name,
            'format_type': self.export_format,
            'clean_image': True,
            'keep_image': True,
            # TODO: Upload support for S3/Swift.. some day ?
            'upload': False,
            'download_dir': settings.LOCAL_STORAGE,
            'download_location': self._extract_os_file_location(settings.LOCAL_STORAGE),
            'snapshot_id': None,
            'image_id': None,
            'volume_id': None,
            'instance_id': None,
        }
        source = self.source
        if source.is_volume():
            default_kwargs['volume_id'] = source.identifier
        elif source.is_machine():
            default_kwargs['image_id'] = source.identifier
        elif source.is_snapshot():
            default_kwargs['snapshot_id'] = self.source.identifier
        # NOTE:  Instance-exporting is also possible in OpenStack,
        # but we would need new models to support it.
        #

        return default_kwargs

    def __unicode__(self):
        return '%s ExportRequest of %s: %s Status:%s'\
            % (self.export_owner,
               self.source.source_type, self.source.identifier,
               self.status)

    class Meta:
        db_table = "export_request"
        app_label = "core"
