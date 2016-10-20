"""
  Machine models for atmosphere.
"""
import json
import re
import os

from django.db import models
from django.db.models import Q, Model
from django.core.exceptions import ValidationError
from django.utils import timezone
from core.models.user import AtmosphereUser as User

from core.models.application import create_application, ApplicationThreshold
from core.models.license import License
from core.models.boot_script import BootScript
from core.models.machine import ProviderMachine
from core.models.node import NodeController
from core.models.provider import Provider
from core.models.identity import Identity
from core.models.application_version import ApplicationVersion

from atmosphere.settings import secrets
from threepio import logger
from core.models.abstract import BaseRequest
from core.exceptions import RequestLimitExceeded
from functools import reduce

UNRESOLVED_STATES = ["pending", "processing", "validated", "failed"]

class MachineRequest(BaseRequest):

    """
    Storage container for the MachineRequestThread to start/restart the Queue
    Provides a Parent-Child relationship between the new image and ancestor(s)
    """


    # The instance to image.
    instance = models.ForeignKey("Instance")

    old_status = models.TextField(default="", null=True, blank=True)

    # Machine imaging Metadata
    parent_machine = models.ForeignKey(ProviderMachine,
                                       related_name="ancestor_machine")

    # Data for the new machine, version and app...
    # Application specific:
    new_application_name = models.CharField(max_length=256)
    new_application_description = models.TextField(
        default='Description Missing')
    new_application_visibility = models.CharField(
        max_length=256, default='private')  # Choices:Public, Private, Select
    access_list = models.TextField(
        default='',
        blank=True,
        null=True)  # DEPRECATED in API v2
    # SPECIFIC to 'forked=False'

    # Specific to ApplicationVersion && ProviderMachine
    system_files = models.TextField(default='', blank=True, null=True)
    installed_software = models.TextField(default='', blank=True, null=True)
    exclude_files = models.TextField(default='', blank=True, null=True)
    new_version_name = models.CharField(max_length=256, default='1.0')
    new_version_change_log = models.TextField(default='Changelog Missing')
    new_version_tags = models.TextField(
        default='', blank=True, null=True)  # Re-rename to new_application_tags
    new_version_memory_min = models.IntegerField(default=0)
    new_version_cpu_min = models.IntegerField(default=0)
    new_version_allow_imaging = models.BooleanField(default=True)
    new_version_forked = models.BooleanField(default=True)
    new_version_licenses = models.ManyToManyField(License, blank=True)
    new_version_scripts = models.ManyToManyField(BootScript, blank=True)
    new_version_membership = models.ManyToManyField("Group", blank=True)

    new_machine_provider = models.ForeignKey(Provider)
    new_machine_owner = models.ForeignKey(User, related_name="new_image_owner")
    
    # Date time stamps
    #start_date = models.DateTimeField(default=timezone.now)
    #end_date = models.DateTimeField(null=True, blank=True)

    # Filled in when completed.
    # NOTE: ProviderMachine and 'new_machine' might be phased out
    # along with 'new_machine_provider' as Versions become replicated
    # across different clouds.
    # However, it might be good to have the "Original machine"..
    # similar to the 'created_by/created_by_identity' dilemma
    new_machine = models.ForeignKey(ProviderMachine,
                                    null=True, blank=True)
    new_application_version = models.ForeignKey(ApplicationVersion,
                                                null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.pk and self.is_active(self.instance):
            raise RequestLimitExceeded(
                    "The number of open requests for "
                    "instance %s has been exceeded."
                    % self.instance.provider_alias)
        Model.save(self, *args, **kwargs)

    @classmethod
    def is_active(cls, instance):
        """
        """
        return cls.objects.filter(instance=instance,
                status__name__in=UNRESOLVED_STATES).count() > 0

    def clean(self):
        """
        Clean up machine requests before saving initial objects to allow
        users the chance to correct their mistakes.
        """
        # 'Created application' specific logic that should fail:
        if self.new_version_forked:
            pass
        # 'Updated Version' specific logic that should fail:
        else:
            if self.new_application_name:
                raise ValidationError(
                    "Application name cannot be set unless a new application "
                    "is being created. Remove the Application name to update "
                    "-OR- fork the existing application")

        # General Validation && AutoCompletion
        if self.access_list:
            self.new_version_membership = _match_membership_to_access(
                self.access_list,
                self.new_version_membership)

        # Automatically set 'end date' when completed
        #TODO: verify this should be 'old_status' or change it to a StatusType
        if self.old_status == 'completed' and not self.end_date:
            self.end_date = timezone.now()

    def new_version_threshold(self):
        return {'memory': self.new_version_memory_min,
                'cpu': self.new_version_cpu_min}

    def get_request_status(self):
        return self.status.name

    def get_app(self):
        if self.new_machine:
            return self.new_machine.application
        # Return the parent application if the new machine has not been
        # created.
        return self.parent_machine.application

    def get_version(self):
        if self.new_machine:
            return self.new_machine.application_version
        return None

    def update_threshold(self):
        application_version = self.get_version()
        existing_threshold = ApplicationThreshold.objects.filter(
            application_version=application_version)

        if existing_threshold:
            threshold = existing_threshold[0]
        else:
            threshold = ApplicationThreshold(
                application_version=application_version)

        threshold.memory_min = self.new_version_memory_min
        threshold.cpu_min = self.new_version_cpu_min
        threshold.save()
        return threshold

    def has_threshold(self):
        return self.new_version_memory_min > 0\
            or self.new_version_cpu_min > 0

    def migrate_access_to_membership_list(self, access_list):
        for user in access_list:
            # 'User' -> User -> Group -> Membership
            user_qs = User.objects.filter(username=user)
            if not user_qs.exists():
                logger.warn("WARNING: User %s does not have a user object" % user)
                continue
            usergroup_qs = user_qs[0].group_set.filter(name=user)
            if not usergroup_qs:
                logger.warn("WARNING: User %s does not have a group object" % user)
                continue
            group = usergroup_qs[0]
            self.new_version_membership.add(group)

    def _get_meta_name(self):
        """
        admin_<username>_<name_under_scored>_<mmddyyyy_hhmmss>
        """
        meta_name = '%s_%s_%s_%s' %\
            ('admin', self.new_machine_owner.username,
             self.new_application_name.replace(' ', '_').replace('/', '-'),
             self.start_date.strftime('%m%d%Y_%H%M%S'))
        return meta_name

    def fix_metadata(self, im):
        if not self.new_machine:
            raise Exception(
                "New machine missing from machine request. Cannot Fix.")
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
            raise Exception(
                "Kernel/Ramdisk information MISSING "
                "from previous machine. "
                "Fix NOT required")
        properties.update(
            {'kernel_id': previous_kernel, 'ramdisk_id': previous_ramdisk})
        im.update_image(new_mach, properties=properties)

    def old_provider(self):
        return self.instance.source.provider

    def new_machine_id(self):
        if self.new_machine:
            return self.new_machine.identifier
        else:
            return None

    def instance_alias(self):
        return self.instance.provider_alias

    def is_public(self):
        return "public" in self.new_application_visibility.lower()

    def get_access_list(self):
        if '[' not in self.access_list:
            json_loads_list = str(self.access_list.split(", "))
            # New Format = "[u'test1', u'test2', u'test3']"
        else:
            json_loads_list = self.access_list
        json_loads_list = json_loads_list.replace("'", '"').replace('u"', '"')
        user_list = json.loads(json_loads_list)
        return user_list

    def parse_access_list(self):
        user_list = re.split(', | |\n', self.access_list)
        return user_list

    def get_exclude_files(self):
        exclude = re.split(", | |\n", self.exclude_files)
        return exclude

    def old_admin_identity(self):
        old_provider = self.parent_machine.provider
        old_admin = old_provider.get_admin_identity()
        return old_admin

    def new_admin_identity(self):
        new_provider = self.new_machine_provider
        new_admin = new_provider.get_admin_identity()
        return new_admin

    def active_provider(self):
        active_provider = self.new_machine_provider
        if not active_provider:
            active_provider = self.parent_machine.provider
        return active_provider

    def get_credentials(self):
        old_provider = self.parent_machine.provider
        old_creds = old_provider.get_credentials()
        old_admin = old_provider.get_admin_identity().get_credentials()
        if 'ex_force_auth_version' not in old_creds:
            old_creds['ex_force_auth_version'] = '2.0_password'
        old_creds.update(old_admin)

        new_provider = self.new_machine_provider
        if old_provider.id == new_provider.id:
            new_creds = old_creds.copy()
        else:
            new_creds = new_provider.get_credentials()
            if 'ex_force_auth_version' not in new_creds:
                new_creds['ex_force_auth_version'] = '2.0_password'
            new_admin = new_provider.get_admin_identity().get_credentials()
            new_creds.update(new_admin)

        return (old_creds, new_creds)

    def prepare_manager(self):
        """
        Prepares, but does not initialize, manager(s)
        This allows the manager and required credentials to be passed to celery
        without causing serialization errors
        """
        from chromogenic.drivers.openstack import \
            ImageManager as OSImageManager
        from chromogenic.drivers.eucalyptus import \
            ImageManager as EucaImageManager

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
            download_location, '%s.qcow2' % self.new_application_name)
        return download_location

    def get_imaging_args(self, debug=False):
        """
        Prepares the entire machine request for serialization to celery

        """
        from chromogenic.drivers.openstack import \
            ImageManager as OSImageManager
        from chromogenic.drivers.eucalyptus import \
            ImageManager as EucaImageManager

        (orig_managerCls, orig_creds,
         dest_managerCls, dest_creds) = self.prepare_manager()

        download_dir = secrets.LOCAL_STORAGE

        imaging_args = {
            "visibility": self.new_application_visibility,
            "instance_id": self.instance.provider_alias,
            #NOTE: THERE IS AN ASSUMPTION MADE HERE!
            # ASSUMPTION: the Creator's username == the LINUX username that was also created for them!
            #FIXME if the ASSUMPTION above changes!
            "created_by": self.instance.created_by.username,
            "remove_image": True,
            "remove_local_image": True,
            "upload_image": True,
            "image_name": self.new_application_name,
            "timestamp": self.start_date,
            "download_dir": download_dir
        }
        if debug:
            # NOTE: use the `parent_image_id` value *OR* `instance_id` value
            # If you are setting debug=True, you're calling from the REPL,
            # and you must be responsible for deciding
            # which of those two values you would like to .pop()
            # You should use the 'instance_id' field if
            # you need to snapshot the instance first.
            # You should use the 'parent_image_id' field if
            # you want to debug a glance image
            # Usually, this will contain the new_machine.identifier,
            # but possibly the instances boot-source will be required for debug
            imaging_args['parent_image_id'] = self.new_machine.identifier if self.new_machine else self.instance.source.identifier
            imaging_args['upload_image'] = False  # Set to False to keep Snapshot or parent_image_id in glance
            imaging_args['remove_image'] = False  # Set to False to keep Snapshot or parent_image_id in glance
            imaging_args['remove_local_image'] = False  # Set to False to keep downloaded file
            # NOTE: If you run with the debug setup above,
            # the *only* operation that will be completed
            # is the *download* the instance/image
            # and then *clean* the file.
            # Set to False to skip the 'clean' portion and only download the instance/image.
            #imaging_args['clean_image'] = False

        if issubclass(orig_managerCls, OSImageManager):
            download_location = self._extract_file_location(download_dir)
            imaging_args['download_location'] = download_location
        elif issubclass(orig_managerCls, EucaImageManager):
            euca_args = self._prepare_euca_args()
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

    def _prepare_euca_args(self):
        meta_name = self._get_meta_name()
        public_image = self.is_public()
        # Splits the string by ", " OR " " OR "\n" to create the list
        private_users = self.parse_access_list()
        exclude = self.get_exclude_files()
        # Create image on image manager
        (orig_managerCls, orig_creds,
         dest_managerCls, dest_creds) = self.prepare_manager()
        node_scp_info = self.get_euca_node_info(orig_managerCls, orig_creds)
        return {
            "public": public_image,
            "private_user_list": private_users,
            "exclude": exclude,
            "meta_name": meta_name,
            "node_scp_info": node_scp_info,
        }

    def get_euca_node_info(self, euca_managerCls, euca_creds):
        node_dict = {
            'hostname': '',
            'port': '',
            'private_key': ''
        }
        instance_id = self.instance.provider_alias
        # Prepare and use the manager
        euca_manager = euca_managerCls(**euca_creds)
        node_ip = euca_manager.get_instance_node(instance_id)

        # Find the matching node
        try:
            core_node = NodeController.objects.get(alias=node_ip)
            node_dict['hostname'] = core_node.hostname
            node_dict['port'] = core_node.port
            node_dict['private_key'] = core_node.private_ssh_key
        except NodeController.DoesNotExist:
            logger.error("Must create a nodecontroller for IP: %s" % node_ip)
        # Return a dict containing information on how to SCP to the node
        return node_dict

    def __unicode__(self):
        return '%s Instance: %s Name: %s Status: %s (%s)'\
            % (self.new_machine_owner, self.instance.provider_alias,
               self.new_application_name, self.old_status, self.status)

    class Meta:
        db_table = "machine_request"
        app_label = "core"


def _match_membership_to_access(access_list, membership):
    """
    INPUT: user1,user2, user3 + user4,user5
    OUTPUT: <User: 1>, ..., <User: 5>
    """
    # Circ.Dep. DO NOT MOVE UP!! -- Future Solve:Move into Group?
    from core.models.group import Group
    if not access_list:
        return membership.all()
    # If using access list, parse the list
    # into queries and evaluate the filter ONCE.
    names_wanted = access_list.split(',')
    query_list = map(lambda name: Q(name__iexact=name), names_wanted)
    query_list = reduce(lambda qry1, qry2: qry1 | qry2, query_list)
    members = Group.objects.filter(query_list)
    return members | membership.all()


def _create_new_application(machine_request, new_image_id, tags=[]):
    new_provider = machine_request.new_machine_provider
    user = machine_request.new_machine_owner
    owner_ident = Identity.objects.get(created_by=user, provider=new_provider)
    # This is a brand new app and a brand new providermachine
    new_app = create_application(
        new_provider.id,
        new_image_id,
        machine_request.new_application_name,
        owner_ident,
        # new_app.Private = False when machine_request.is_public = True
        not machine_request.is_public(),
        machine_request.new_machine_version,
        machine_request.new_machine_description,
        tags)
    return new_app


def _update_parent_application(machine_request, new_image_id, tags=[]):
    parent_app = machine_request.instance.source.providermachine.application
    return _update_application(parent_app, machine_request, tags=tags)


def _update_application(application, machine_request, tags=[]):
    if application.name is not machine_request.new_application_name:
        application.name = machine_request.new_application_name
    if machine_request.new_machine_description:
        application.description = machine_request.new_machine_description
    application.private = not machine_request.is_public()
    application.tags = tags
    application.save()
    return application


def _update_existing_machine(machine_request, application, provider_machine):
    new_provider = machine_request.new_machine_provider
    user = machine_request.new_machine_owner
    owner_ident = Identity.objects.get(created_by=user, provider=new_provider)

    provider_machine.application = application
    provider_machine.version = machine_request.new_machine_version
    provider_machine.created_by = user
    provider_machine.created_by_identity = owner_ident
    provider_machine.save()
