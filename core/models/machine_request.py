"""
  Machine models for atmosphere.
"""
import json
import re
import os

from django.db import models
from django.utils import timezone
from core.models.user import AtmosphereUser as User


from core.models.application import update_application, create_application, ApplicationMembership
from core.models.license import License
from core.models.machine import create_provider_machine, ProviderMachine, update_provider_machine, provider_machine_write_hook
from core.models.node import NodeController
from core.models.provider import Provider, AccountProvider
from core.models.identity import Identity

from atmosphere.settings import secrets
from threepio import logger


class MachineRequest(models.Model):
    """
    Storage container for the MachineRequestThread to start/restart the Queue
    Provides a Parent-Child relationship between the new image and ancestor(s)
    """
    # The instance to image.
    instance = models.ForeignKey("Instance")

    # Machine imaging Metadata
    status = models.TextField(default='', blank=True)
    parent_machine = models.ForeignKey(ProviderMachine,
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
    new_machine_version = models.CharField(max_length=128, default='1.0.0')
    new_machine_forked = models.BooleanField(default=True)
    new_machine_memory_min = models.IntegerField(default=0)
    new_machine_storage_min = models.IntegerField(default=0)
    new_machine_licenses = models.ManyToManyField(License,
            blank=True)
    new_machine_allow_imaging = models.BooleanField(default=True)
    #Date time stamps
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)

    # Filled in when completed.
    new_machine = models.ForeignKey(ProviderMachine,
                                    null=True, blank=True,
                                    related_name="created_machine")

    def new_machine_threshold(self):
        return {'memory': self.new_machine_memory_min,
                'disk': self.new_machine_storage_min }
    def get_app(self):
        if self.new_machine:
            return self.new_machine.application
        #Return the parent application if the new machine has not been created.
        return self.parent_machine.application

    def update_threshold(self):
        application = self.get_app()
        existing_threshold = ApplicationThreshold.objects.filter(
                application=application)

        if existing_threshold:
            threshold = existing_threshold[0]
        else:
            threshold = ApplicationThreshold(application=application)

        threshold.memory_min=machine_request.new_machine_memory_min
        threshold.storage_min=machine_request.new_machine_storage_min
        threshold.save()
        return threshold

    def has_threshold(self):
        return self.new_machine_memory_min > 0\
                or self.new_machine_storage_min > 0

    def _get_meta_name(self):
        """
        admin_<username>_<name_under_scored>_<mmddyyyy_hhmmss>
        """
        meta_name = '%s_%s_%s_%s' %\
            ('admin', self.new_machine_owner.username,
            self.new_machine_name.replace(' ','_').replace('/','-'),
            self.start_date.strftime('%m%d%Y_%H%M%S'))
        return meta_name

    def fix_metadata(self, im):
        if not self.new_machine:
            raise Exception("New machine missing from machine request. Cannot Fix.")
        (orig_managerCls, orig_creds,
         dest_managerCls, dest_creds) = self.prepare_manager()
        im = dest_managerCls(**dest_creds)
        old_mach_id = self.instance.source.identifier
        new_mach_id = self.new_machine.identifier
        old_mach = im.get_image(old_mach_id)
        if not old_mach:
            raise Exception("Could not find old machine.. Cannot Fix.")
        new_mach = im.get_image(new_mach_id)
        if not old_mach:
            raise Exception("Could not find new machine.. Cannot Fix.")
        properties = new_mach.properties
        previous_kernel = old_mach.properties.get('kernel_id')
        previous_ramdisk = old_mach.properties.get('ramdisk_id')
        if not previous_kernel or previous_ramdisk:
            raise Exception("Kernel/Ramdisk information MISSING from previous machine. Fix NOT required")
        properties.update({'kernel_id': previous_kernel, 'ramdisk_id': previous_ramdisk})
        im.update_image(new_mach, properties=properties)

    def old_provider(self):
        return self.instance.source.provider

    def new_machine_id(self):
        return 'zzz%s' % self.new_machine.identifier if self.new_machine else None

    def instance_alias(self):
        return self.instance.provider_alias

    def is_public(self):
        return "public" in self.new_machine_visibility.lower()

    def get_access_list(self):
        if '[' not in self.access_list:
            #Format = "test1, test2, test3"
            json_loads_list = str(self.access_list.split(", "))
            #New Format = "[u'test1', u'test2', u'test3']"
        else:
            #Format = "[u'test1', u'test2', u'test3']"
            json_loads_list = self.access_list
        json_loads_list = json_loads_list.replace("'",'"').replace('u"', '"')
        user_list = json.loads(json_loads_list)
        return user_list

    def parse_access_list(self):
        user_list=re.split(', | |\n', self.access_list)
        return user_list

    def get_exclude_files(self):
        exclude=re.split(", | |\n", self.exclude_files)
        return exclude

    def old_admin_identity(self):
        old_provider = self.parent_machine.provider
        old_admin = old_provider.get_admin_identity()
        return old_admin

    def new_admin_identity(self):
        new_provider = self.new_machine_provider
        new_admin = new_provider.get_admin_identity()
        return new_admin

    def new_admin_driver(self):
        from service.driver import get_admin_driver
        return get_admin_driver(self.new_machine_provider)

    def active_provider(self):
        active_provider = self.new_machine_provider
        if not active_provider:
            active_provider = self.parent_machine.provider
        return active_provider


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

    def _extract_file_location(self, download_dir):
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
        download_location = os.path.join(
                download_dir, tenant_cred.value)
        download_location = os.path.join(
                download_location, '%s.qcow2' % self.new_machine_name)
        return download_location
    def get_imaging_args(self):
        """
        Prepares the entire machine request for serialization to celery

        TODO: Add things like description and tags to export and migration drivers
        """
        from chromogenic.drivers.openstack import ImageManager as OSImageManager
        from chromogenic.drivers.eucalyptus import ImageManager as EucaImageManager

        (orig_managerCls, orig_creds,
         dest_managerCls, dest_creds) = self.prepare_manager()
    
        download_dir = secrets.LOCAL_STORAGE
    
        imaging_args = {
            "instance_id": self.instance.provider_alias,
            "image_name": self.new_machine_name,
            "download_dir" : download_dir}
        if issubclass(orig_managerCls, OSImageManager):
            download_location = self._extract_file_location(download_dir)
            imaging_args['download_location'] = download_location 
        elif issubclass(orig_managerCls, EucaImageManager):
            euca_args = _prepare_euca_args()
            imaging_args.update(euca_args)

        orig_provider = self.parent_machine.provider
        dest_provider = self.new_machine_provider
        orig_platform = orig_provider.get_platform_name().lower()
        dest_platform = dest_provider.get_platform_name().lower()

        if orig_platform != dest_platform:
            if orig_platform == 'kvm' and dest_platform == 'xen':
                imaging_args['kvm_to_xen'] = True
            elif orig_platform == 'xen' and dest_platform == 'kvm':
                imaging_args['xen_to_kvm'] = True
        return imaging_args

    def _prepare_euca_args():
        meta_name = self._get_meta_name()
        public_image = self.is_public()
        #Splits the string by ", " OR " " OR "\n" to create the list
        private_users = self.parse_access_list()
        exclude = self.get_exclude_files()
        #Create image on image manager
        node_scp_info = self.get_euca_node_info(orig_managerCls, orig_creds)
        euca_args = {
            "public" : public_image,
            "private_user_list" : private_users,
            "exclude" : exclude,
            "meta_name" : meta_name,
            "node_scp_info" : node_scp_info,
        }

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

        #Find the matching node
        try:
            core_node = NodeController.objects.get(alias=node_ip)
            node_dict['hostname'] = core_node.hostname
            node_dict['port'] = core_node.port
            node_dict['private_key'] = core_node.private_ssh_key
        except NodeController.DoesNotExist:
            logger.error("Must create a nodecontroller for IP: %s" % node_ip)
        #Return a dict containing information on how to SCP to the node
        return node_dict

    def __unicode__(self):
        return '%s Instance: %s Name: %s Status: %s'\
                % (self.new_machine_owner, self.instance.provider_alias,
                   self.new_machine_name, self.status)

    class Meta:
        db_table = "machine_request"
        app_label = "core"


def _match_tags_to_names(tag_names):
    """
    INPUT: tag1,tag2,tag3
    OUTPUT: <Tag: tag1>, ..., <Tag: tag3>
    NOTE: Tags NOT created BEFORE being added to new_machine_tags are ignored.
    """
    from core.models.tag import Tag
    tags = [Tag.objects.filter(name__iexact=tag)[0] for tag in
            tag_names.split(',')]
    return tags

def _get_owner(new_provider, user):
    try:
        return Identity.objects.get(provider=new_provider, created_by=user)
    except Identity.DoesNotExist:
        return new_provider.admin

def _create_new_application(machine_request, new_image_id, tags=[]):
    from core.models import Identity
    new_provider = machine_request.new_machine_provider
    user = machine_request.new_machine_owner
    owner_ident = Identity.objects.get(created_by=user, provider=new_provider)
    # This is a brand new app and a brand new providermachine
    new_app = create_application(
            new_image_id,
            new_provider.id,
            machine_request.new_machine_name, 
            owner_ident,
            #new_app.Private = False when machine_request.is_public = True
            not machine_request.is_public(),
            machine_request.new_machine_version,
            machine_request.new_machine_description,
            tags)
    return new_app

def _update_parent_application(machine_request, new_image_id, tags=[]):
    parent_app = machine_request.instance.source.providermachine.application
    return _update_application(parent_app, machine_request, tags=tags)

def _update_application(application, machine_request, tags=[]):
    if application.name is not machine_request.new_machine_name:
        application.name = machine_request.new_machine_name
    if machine_request.new_machine_description:
        application.description = machine_request.new_machine_description
    application.private = not machine_request.is_public()
    application.tags = tags
    application.save()
    return application

def _update_existing_machine(machine_request, application, provider_machine):
    from core.models import Identity
    new_provider = machine_request.new_machine_provider
    user = machine_request.new_machine_owner
    owner_ident = Identity.objects.get(created_by=user, provider=new_provider)

    provider_machine.application = application
    provider_machine.version = machine_request.new_machine_version
    provider_machine.created_by = user
    provider_machine.created_by_identity = owner_ident
    provider_machine.save()

def process_machine_request(machine_request, new_image_id, update_cloud=True):
    """
    NOTE: Current process accepts instance with source of 'Image' ONLY! 
          VOLUMES CANNOT BE IMAGED until this function is updated!
    """
    parent_mach = machine_request.instance.provider_machine
    parent_app = machine_request.instance.provider_machine.application
    new_provider = machine_request.new_machine_provider
    new_owner = machine_request.new_machine_owner
    owner_identity = _get_owner(new_provider, new_owner)
    tags = _match_tags_to_names(machine_request.new_machine_tags)
    #TODO: How to add app version here.
    if machine_request.new_machine_forked:
        app = create_application(
            new_image_id,
            new_provider.uuid,
            machine_request.new_machine_name,
            created_by_identity=owner_identity,
            description=machine_request.new_machine_description,
            private=not machine_request.is_public(),
            tags=tags)
    else:
        parent_app = machine_request.instance.source.providermachine.application
        app = update_application(parent_app, machine_request.new_machine_name, machine_request.new_machine_description, tags)

    #2. Create the new InstanceSource and appropriate Object, relations, Memberships..
    if ProviderMachine.test_existence(new_provider, new_image_id):
        pm = ProviderMachine.objects.get(identifier=new_image_id, provider=new_provider)
        pm = update_provider_machine(pm, new_created_by_identity=owner_identity, new_created_by=machine_request.new_machine_owner, new_application=app, new_version=app_version, allow_imaging=machine_request.new_machine_allow_imaging)
    else:
        #TODO: Create APP version first! Then provider machine & Instance Source using the information.
        pm = create_provider_machine(new_image_id, new_provider.uuid, app, owner_identity, app_version)
        provider_machine_write_hook(pm)

    #Must be set in order to ask for threshold information
    machine_request.new_machine = pm

    #3. Associate additional attributes to new application
    if machine_request.has_threshold():
        machine_request.update_threshold()

    #3. Add new *Memberships For new ProviderMachine//Application
    if not machine_request.is_public():
        upload_privacy_data(machine_request, pm)

    #5. Advance the state of machine request
    machine_request.end_date = timezone.now()
    #After processing, validate the image.
    machine_request.status = 'validating'
    machine_request.save()
    return machine_request

def upload_privacy_data(machine_request, new_machine):
    from service.driver import get_admin_driver, get_account_driver
    prov = new_machine.provider
    accounts = get_account_driver(prov)
    if not accounts:
        print "Aborting import: Could not retrieve Account Driver "\
                "for Provider %s" % prov
        return
    admin_driver = get_admin_driver(prov)
    if not admin_driver:
        print "Aborting import: Could not retrieve admin_driver "\
                "for Provider %s" % prov
        return
    img = accounts.get_image(new_machine.identifier)
    tenant_list = machine_request.get_access_list()
    #All in the list will be added as 'sharing' the OStack img
    #All tenants already sharing the OStack img will be added to this list
    tenant_list = sync_image_access_list(accounts, img, names=tenant_list)
    #Make private on the DB level
    make_private(accounts.image_manager, img, new_machine, tenant_list)



def share_with_admins(private_userlist, provider_uuid):
    """
    NOTE: This will always work, but the userlist could get long some day.
    Another option would be to create an 'admin' tenant that all of core
    services and the admin are members of, and add only that tenant to the
    list.
    """
    if type(private_userlist) != list:
        raise Exception("Expected private_userlist to be list, got %s: %s"
                        % (type(private_userlist), private_userlist))

    from authentication.protocol.ldap import get_core_services
    core_services = get_core_services()
    admin_users = [ap.identity.created_by.username for ap in
                   AccountProvider.objects.filter(provider__uuid=provider_uuid)]
    private_userlist.extend(core_services)
    private_userlist.extend(admin_users)
    return private_userlist

def share_with_self(private_userlist, username):
    if type(private_userlist) != list:
        raise Exception("Expected type(private_userlist) to be list, got %s: %s"
                        % (type(private_userlist), private_userlist))

    #TODO: Optionally, Lookup username and get the Projectname
    private_userlist.append(str(username))
    return private_userlist

def sync_image_access_list(accounts, img, names=None):
    projects = []
    shared_with = accounts.image_manager.shared_images_for(
            image_id=img.id)
    #if not shared_with:
    #    return tenant_names
    #Find tenants who are marked as 'sharing' on openstack but not on DB
    #Or just in One-line..
    projects = [accounts.get_project_by_id(member.member_id) for member in shared_with]
    #Any names who aren't already on the image should be added
    #Find names who are marekd as 'sharing' on DB but not on OpenStack
    for name in names:
        project = accounts.get_project(name)
        if project and project not in projects:
            print "Sharing image %s with project named %s" \
                    % (img.id, name)
            accounts.image_manager.share_image(img, name)
            projects.append(project)
    return projects

def make_private(image_manager, image, provider_machine, tenant_list=[]):
    #Circ.Dep. DO NOT MOVE UP!!
    from core.models import Group, ProviderMachineMembership

    if image.is_public == True:
        print "Marking image %s private" % image.id
        image_manager.update_image(image, is_public=False)
    if provider_machine.application.private == False:
        print "Marking application %s private" % provider_machine.application
        provider_machine.application.private = True
        provider_machine.application.save()
    #Add all these people by default..
    owner = provider_machine.application.created_by
    group_list = owner.group_set.all()
    if tenant_list:
        #ASSERT: Groupnames == Usernames
        tenant_list.extend([group.name for group in group_list])
    else:
        tenant_list = [group.name for group in group_list]
    for tenant in tenant_list:
        name = tenant.name
        group = Group.objects.get(name=name)
        obj, created = ApplicationMembership.objects.get_or_create(
                group=group, 
                application=provider_machine.application)
        if created:
            print "Created new ApplicationMembership: %s" \
                % (obj,)
        obj, created = ProviderMachineMembership.objects.get_or_create(
                group=group,
                provider_machine=provider_machine)
        if created:
            print "Created new ProviderMachineMembership: %s" \
                % (obj,)
