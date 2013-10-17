"""
  Machine models for atmosphere.
"""
import re

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


from core.models.provider import Provider
from core.models.machine import create_provider_machine
from core.models.node import NodeController

from atmosphere import settings
from threepio import logger

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


    def _get_meta_name(self):
        """
        admin_<username>_<name_under_scored>_<mmddyyyy_hhmmss>
        """
        meta_name = '%s_%s_%s_%s' %\
            ('admin', self.new_machine_owner.username,
            self.new_machine_name.replace(' ','_').replace('/','-'),
            self.start_date.strftime('%m%d%Y_%H%M%S'))
        return meta_name

    def is_public(self):
        return "public" in self.new_machine_visibility.lower()

    def get_access_list(self):
        user_list=re.split(', | |\n', self.access_list)
        return user_list

    def get_exclude_files(self):
        exclude=re.split(", | |\n", self.exclude_files)
        return exclude

    def get_credentials(self):
        old_provider = self.parent_machine.provider
        old_creds = old_provider.get_credentials()
        old_admin = old_provider.get_admin_identity().get_credentials()
        old_creds.update(old_admin)

        new_provider = self.new_machine_provider
        if old_provider.id == new_provider.id:
            new_creds = old_creds.copy()
        else:
            new_creds = new_provider.get_credentials()
            new_admin = new_provider.get_admin_identity().get_credentials()
            new_creds.update(new_admin)
        return (old_creds, new_creds)

    def prepare_manager(self):
        """
        Prepares, but does not initialize, manager(s)
        This allows the manager and required credentials to be passed to celery
        without causing serialization errors
        """
        from chromogenic.drivers.openstack import ImageManager as OSImageManager
        from chromogenic.drivers.eucalyptus import ImageManager as EucaImageManager

        orig_provider = self.parent_machine.provider
        dest_provider = self.new_machine_provider
        orig_type = orig_provider.get_type_name().lower()
        dest_type = dest_provider.get_type_name().lower()

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

        orig_creds, dest_creds = self.get_credentials()
        orig_creds = origCls._build_image_creds(orig_creds)
        dest_creds = destCls._build_image_creds(dest_creds)

        return (origCls, orig_creds, destCls, dest_creds)

    def get_imaging_args(self):
        """
        Prepares the entire machine request for serialization to celery

        TODO: Add things like description and tags to export and migration drivers
        """
        from chromogenic.drivers.openstack import ImageManager as OSImageManager
        from chromogenic.drivers.eucalyptus import ImageManager as EucaImageManager

        (orig_managerCls, orig_creds,
         dest_managerCls, dest_creds) = self.prepare_manager()
    
        download_dir = settings.LOCAL_STORAGE
    
        imaging_args = {
            "instance_id": self.instance.provider_alias,
            "image_name": self.new_machine_name,
            "download_dir" : download_dir}
        if issubclass(orig_managerCls, EucaImageManager):
            meta_name = self._get_meta_name()
            public_image = self.is_public()
            #Splits the string by ", " OR " " OR "\n" to create the list
            private_users = self.get_access_list()
            exclude = self.get_exclude_files()
            #Create image on image manager
            node_scp_info = self.get_euca_node_info(orig_managerCls, orig_creds)
            imaging_args.update({
                "public" : public_image,
                "private_user_list" : private_users,
                "exclude" : exclude,
                "meta_name" : meta_name,
                "node_scp_info" : node_scp_info,
            })
        return imaging_args

    def get_euca_node_info(self, euca_managerCls, euca_creds):
        instance_id = self.instance.provider_alias
        #Prepare and use the manager
        euca_manager = euca_managerCls(**euca_creds)
        node_ip = euca_manager.get_instance_node(instance_id)
        #Find the matching node
        try:
            core_node = NodeController.objects.get(alias=node_ip)
        except NodeController.DoesNotExist:
            logger.error("Must create a nodecontroller for IP: %s" % node_ip)
            return None
    
        #Return a dict containing information on how to SCP to the node
        node_dict = {
                'hostname':core_node.hostname,
                'port':core_node.port,
                'private_key':core_node.private_ssh_key
        }
        return node_dict

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
    from core.models import Identity, ProviderMachine
    #Build the new provider-machine object and associate
    try:
	new_machine = ProviderMachine.objects.get(identifier=new_image_id)
    except ProviderMachine.DoesNotExist:
    	new_machine = create_provider_machine(
    	    machine_request.new_machine_name, new_image_id,
    	    machine_request.new_machine_provider_id)

    new_identity = Identity.objects.get(created_by=machine_request.new_machine_owner, provider=machine_request.new_machine_provider)
    generic_mach = new_machine.machine
    tags = [Tag.objects.get(name__iexact=tag) for tag in
            machine_request.new_machine_tags.split(',')] \
        if machine_request.new_machine_tags else []
    generic_mach.created_by = machine_request.new_machine_owner
    generic_mach.created_by_identity = new_identity
    generic_mach.tags = tags
    generic_mach.description = machine_request.new_machine_description
    generic_mach.save()
    new_machine.created_by = machine_request.new_machine_owner
    new_machine.created_by_identity = new_identity
    new_machine.save()
    machine_request.new_machine = new_machine
    machine_request.end_date = timezone.now()
    machine_request.status = 'completed'
    machine_request.save()
    return machine_request
