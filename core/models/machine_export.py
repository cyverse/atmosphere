import os

from django.db import models
from django.utils import timezone
from django.conf import settings
from core.models.user import AtmosphereUser as User
from atmosphere.settings import secrets

from chromogenic.drivers.virtualbox import ImageManager as VBoxManager
from chromogenic.drivers.openstack import ImageManager as OSImageManager
from chromogenic.drivers.eucalyptus import ImageManager as EucaImageManager

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
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    #TODO: Perhaps a field for the MD5 Hash?
    def get_admin_provider(self):
        return self.instance.provider_machine.provider

    def get_admin_driver(self):
        old_provider = self.get_admin_provider()
        admin_driver = get_admin_driver(old_provider)
        return admin_driver

    def get_credentials(self):
        prov = self.get_admin_provider()
        creds = prov.get_credentials()
        admin_creds = prov.get_admin_identity().get_credentials()
        creds.update(admin_creds)
        return creds

    def _extract_os_file_location(self, download_dir):
        #Openstack snapshots are saved as a QCOW2
        ext = "qcow2"
        id_owner = self.instance.created_by_identity
        tenant_cred = id_owner.credential_set.filter(
                key='ex_tenant_name')
        if not tenant_cred:
            tenant_cred = id_owner.credential_set.filter(
                    key='ex_project_name')
        if not tenant_cred:
            raise Exception("You should not be here! Update the key "
                    "used for openstack tenant names!")
        tenant_cred = tenant_cred[0]
        download_location = os.path.join(download_dir, tenant_cred.value)
        download_location = os.path.join(download_location, '%s.%s' % (self.export_name, ext))
        return download_location

    def get_export_args(self):
        download_dir = secrets.LOCAL_STORAGE
        (orig_managerCls, orig_creds, dest_managerCls) = self.prepare_manager()
        export_args = {
                "keep_image": True,
                "instance_id": self.instance.provider_alias,
                "format":self.export_format,
                "name":self.export_name,
                "download_dir": download_dir
        }
        if issubclass(orig_managerCls, OSImageManager):
            download_location = self._extract_os_file_location(download_dir)
            export_args['download_location'] = download_location 
        elif issubclass(orig_managerCls, EucaImageManager):
            euca_args = _prepare_euca_args()
            export_args.update(euca_args)

        #VBox Specific export args.
        if issubclass(dest_managerCls, VBoxManager):
            pass
        return export_args

    def get_euca_node_info(self, euca_managerCls, euca_creds):
        node_dict = {
                'hostname':'',
                'port':'',
                'private_key':''
        }
        instance_id = self.instance.provider_alias
        #Prepare and use the manager
        euca_manager = euca_managerCls(**euca_creds)
        node_ip = euca_manager.get_instance_node(instance_id)

    def _prepare_euca_args(euca_managerCls, euca_creds):
        #Create image on image manager
        node_scp_info = self.get_euca_node_info(euca_managerCls, euca_creds)
        return {
            "node_scp_info" : node_scp_info,
        }

    def prepare_manager(self):
        """
        Prepare, but do not initialize, the Provider's Driver & ExportManager
        """
        provider = self.get_admin_provider()
        provider_type = provider.type.name
        if 'openstack' in provider_type.lower():
            origCls = OSImageManager
        elif 'eucalyptus' in provider_type.lower():
            origCls = EucaImageManager
        else:
            raise ValueError("Provider %s is using an unknown type:%s"
                             % (provider, provider_type))
        #TODO: Logic on where/what to export goes here...
        destCls = VBoxManager
        creds = self.get_credentials()
        return (origCls, creds, destCls)

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
    #Email the user..
