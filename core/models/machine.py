"""
  Machine models for atmosphere.
"""
import json
from hashlib import md5

from django.db import models
from django.utils import timezone
from threepio import logger

from atmosphere import settings
from core.models.abstract import BaseSource
from core.models.instance_source import InstanceSource
from core.models.application import Application
from core.models.application import create_application, get_application
from core.models.identity import Identity
from core.models.license import License
from core.models.provider import Provider
from core.models.tag import Tag, updateTags
from core.fields import VersionNumberField, VersionNumber

from core.metadata import _get_owner_identity
from core.application import get_os_account_driver, write_app_to_metadata,\
                             has_app_metadata, get_app_metadata


class ProviderMachine(BaseSource):
    """
    Machines are created by Providers, and multiple providers
    can implement a single machine (I.e. Ubuntu 12.04)
    However each provider will have a specific, unique identifier
    to represent that machine. (emi-12341234 vs ami-43214321)
    """
    esh = None
    application = models.ForeignKey(Application)
    version = models.CharField(max_length=128, default='1.0.0')
    licenses = models.ManyToManyField(License,
            blank=True)

    @property
    def name(self):
        return self.application.name

    def to_dict(self):
        machine = {
            "version": self.version,
            "provider": self.instance_source.provider.uuid
        }
        machine.update(super(ProviderMachine, self).to_dict())
        return machine

    def update_image(self, **image_updates):
        """
        The acceptable values for image_updates are specific to the image 
        and image_manager, but here are some common examples for an OpenStack
        cloud:
        * name="My New Name"
        * owner=<project_id//tenant_id>
        * min_ram=<RAM_in_MB>
        * min_disk=<Storage_in_GB>
        * is_public=True/False
        You can also REPLACE all values at once using the 'properties' kwarg
        * properties={'metadata_key':'metadata_value',...}
        (More Documentation on this inside the image_manager, chromogenic)
        """
        try:
            from service.driver import get_account_driver
            accounts = get_account_driver(self.provider)
            image = accounts.image_manager.get_image(self.identifier)
            accounts.image_manager.update_image(image, **image_updates)
        except Exception as ex:
            logger.exception("Image Update Failed for %s on Provider %s"
                             % (self.identifier, self.provider))

    def update_version(self, version):
        self.version = version
        self.save()
    
    def icon_url(self):
        return self.application.icon.url if self.application.icon else None

    def save(self, *args, **kwargs):
        #Update values on the application
        self.application.update(**kwargs)
        super(ProviderMachine, self).save(*args, **kwargs)

    def creator_name(self):
        if self.application:
            return self.application.created_by.username
        else:
            return "Unknown"

    def hash_alias(self):
        return md5(self.instance_source.identifier).hexdigest()

    def find_machine_owner(self):
        if self.provider.location == 'EUCALYPTUS':
            pass  # Parse the XML manifest
        return ""

    def esh_architecture(self):
        if self.esh and self.esh._image\
           and self.esh._image.extra:
            return self.esh._image.extra.get('architecture', "N/A")

    def esh_ownerid(self):
        if self.esh and self.esh._image\
           and self.esh._image.extra\
           and self.esh._image.extra.get('metadata'):
            return self.esh._image.extra['metadata'].get('application_owner', "admin")

    def esh_state(self):
        if self.esh and self.esh._image\
           and self.esh._image.extra:
            return self.esh._image.extra['state']

    def __unicode__(self):
        identifier = self.instance_source.identifier
        provider = self.instance_source.provider
        return "%s (Provider:%s - App:%s) " %\
            (identifier, provider, self.application)

    class Meta:
        db_table = "provider_machine"
        app_label = "core"


class ProviderMachineMembership(models.Model):
    """
    Members of a specific image and provider combination.
    Members can view & launch respective machines.
    If the can_share flag is set, then members also have ownership--they can give
    membership to other users.
    The unique_together field ensures just one of those states is true.
    """
    provider_machine = models.ForeignKey(ProviderMachine)
    group = models.ForeignKey('Group')
    can_share = models.BooleanField(default=False)

    def __unicode__(self):
        return "(ProviderMachine:%s - Member:%s) " %\
            (self.provider_machine.identifier, self.group.name)

    class Meta:
        db_table = 'provider_machine_membership'
        app_label = 'core'
        unique_together = ('provider_machine', 'group')


def build_cached_machines():
    #logger.debug("building cached machines")
    machine_dict = {}
    cms = ProviderMachine.objects.all()
    for cm in cms:
        machine_dict[(cm.provider.id, cm.identifier)] = cm
    ProviderMachine.cached_machines = machine_dict
    return machine_dict


"""
Useful utility methods for the Core Model..
"""


def get_cached_machine(provider_alias, provider_id):
    if not ProviderMachine.cached_machines:
        build_cached_machines()
    cached_mach = ProviderMachine.cached_machines.get(
        (int(provider_id), provider_alias))
    if not cached_mach:
        logger.warn("Cache does not have machine %s on provider %s"
                    % (provider_alias, provider_id))
    return cached_mach


def get_or_create_provider_machine(image_id, machine_name, provider_uuid,
                          app=None, metadata={}):
    """
    Guaranteed Return of ProviderMachine.
    1. Load provider machine from DB
    2. If 'Miss':
       * Lookup application based on PM uuid
       If 'Miss':
         * Create application based on PM uuid
    3. Using application from 2. Create provider machine
    """
    provider_machine = get_provider_machine(image_id, provider_uuid)
    if provider_machine:
        return provider_machine
    if not app:
        app = get_application(image_id, machine_name, app_uuid=metadata.get('uuid'))

    #ASSERT: If no application here, this is a new image
    # that was created on a seperate server. We need to make a new one.
    if not app:
        app = create_application(image_id, provider_uuid, machine_name)
    return create_provider_machine(
            machine_name, image_id, provider_uuid,
            app=app, metadata=metadata)

def _extract_tenant_name(identity):
    tenant_name = identity.get_credential('ex_tenant_name')
    if not tenant_name:
        tenant_name = identity.get_credential('ex_project_name')
    if not tenant_name:
        raise Exception("Cannot update application owner without knowing the"
                        " tenant ID of the new owner. Please update your"
                        " identity, or the credential key fields above"
                        " this line.")
    return tenant_name


def update_application_owner(application, identity):
    old_identity = application.created_by_identity
    tenant_name = _extract_tenant_name(identity)
    old_tenant_name = _extract_tenant_name(old_identity)
    #Prepare the application
    application.created_by_identity = identity
    application.created_by = identity.created_by
    application.save()
    #Update all the PMs
    all_pms = application.providermachine_set.all()
    print "Updating %s machines.." % len(all_pms)
    for provider_machine in all_pms:
        accounts = get_os_account_driver(provider_machine.provider)
        image_id = provider_machine.instance_source.identifier
        image = accounts.image_manager.get_image(image_id)
        if not image:
            continue
        tenant_id = accounts.get_project(tenant_name).id
        write_app_to_metadata(provider_machine, owner=tenant_id)
        print "App data saved for %s" % image_id
        accounts.image_manager.share_image(image, tenant_name)
        print "Shared access to %s with %s" % (image_id, tenant_name)
        accounts.image_manager.unshare_image(image, old_tenant_name)
        print "Removed access to %s for %s" % (image_id, old_tenant_name)


def create_provider_machine(machine_name, image_id, provider_uuid, app,
                            metadata={}):
    #Attempt to match machine by provider alias
    #Admin identity used until the real owner can be identified.
    provider = Provider.objects.get(uuid=provider_uuid)

    #TODO: Read admin owner from location IFF eucalyptus
    machine_owner = _get_owner_identity(metadata.get('owner',''), provider_uuid)

    logger.debug("Provider %s" % provider)
    logger.debug("App %s" % app)

    source = InstanceSource.objects.create(
        identifier=image_id,
        created_by=machine_owner.created_by,
        provider=provider,
        created_by_identity=machine_owner,
    )

    provider_machine = ProviderMachine.objects.create(
        application=app,
        version=metadata.get('version', "1.0"),
        instance_source=source
    )
    logger.info("New ProviderMachine created: %s" % provider_machine)
    add_to_cache(provider_machine)
    return provider_machine


def add_to_cache(provider_machine):
    #if not ProviderMachine.cached_machines:
    #    logger.warn("ProviderMachine cache does not exist.. Building.")
    #    build_cached_machines()
    #ProviderMachine.cached_machines[(
    #    provider_machine.provider.id,
    #    provider_machine.identifier)] = provider_machine
    return provider_machine


def _check_for_metadata_update(esh_machine, provider_uuid):
    """
    In this method, we look for specific metadata on an 'esh_machine'
    IF we find the data we are looking for (like application_uuid)
    and we assume that OpenStack is 'the Authority' on this information,
    We can use that to Update/Bootstrap our DB values about the specific
    application and provider machine version.
    """
    name = esh_machine.name
    alias = esh_machine.alias
    if not esh_machine._image:
        metadata = {}
    else:
        metadata = esh_machine._image.extra.get('metadata',{})
    #TODO: lookup the line below and find the 'real' test conditions.
    if metadata and False and has_app_metadata(metadata):
        #USE CASE: Application data exists on the image
        # and may exist on this DB
        app = get_application(alias, name, metadata.get('application_uuid'))
        if not app:
            app_kwargs = get_app_metadata(metadata, provider_uuid)
            logger.debug("Creating Application for Image %s "
                         "(Based on Application data: %s)"
                         % (alias, app_kwargs))
            app = create_application(alias, provider_uuid, **app_kwargs)
        provider_machine = get_or_create_provider_machine(alias, name, provider_uuid,
                                             app=app, metadata=metadata)
        #If names conflict between OpenStack and Database, choose OpenStack.
        if esh_machine._image and app.name != name:
            logger.debug("Name Conflict! Machine %s named %s, Application named %s"
                         % (alias, name, app.name))
            app.name = name
            app.save()
    else:
        #USE CASE: Application data does NOT exist,
        # This machine is assumed to be its own application, so run the
        # machine alias to retrieve any existing application.
        # otherwise create a new application with the same name as the machine
        provider_machine = _load_machine(
                esh_machine, provider_uuid)
    #TODO: some test to verify when we should be 'pushing back' to cloud
    #push_metadata = True
    #if push_metadata and hasattr(esh_driver._connection,
    #                             'ex_set_image_metadata'):
    #    logger.debug("Writing App data for Image %s:%s" % (alias, app.name))
    #    write_app_to_metadata(esh_driver, provider_machine)
    return provider_machine

def get_provider_machine(identifier, provider_uuid):
    try:
        source = InstanceSource.objects.get(
            provider__uuid=provider_uuid, identifier=identifier)
        return source.providermachine
    except InstanceSource.DoesNotExist:
        return None

def _load_machine(esh_machine, provider_uuid):
    name = esh_machine.name
    alias = esh_machine.alias
    app = get_application(alias, name)
    if not app:
        logger.debug("Creating Application for Image %s" % (alias, ))
        app = create_application(alias, provider_uuid, name)
    #Using what we know about our (possibly new) application
    #and load (or possibly create) the provider machine
    provider_machine = get_or_create_provider_machine(
        alias, name, provider_uuid, app=app)
    return provider_machine

def convert_esh_machine(
        esh_driver, esh_machine,
        provider_uuid, user, identifier=None):
    """
    Takes as input an (rtwo) driver and machine, and a core provider id
    Returns as output a core ProviderMachine
    """
    if identifier and not esh_machine:
        return _convert_from_instance(esh_driver, provider_uuid, identifier)
    elif not esh_machine:
        return None

    provider_machine = _load_machine(esh_machine, provider_uuid)

    provider_machine.esh = esh_machine
    return provider_machine


def _check_project(core_application, user):
    """
    Select a/multiple projects the application belongs to.
    NOTE: User (NOT Identity!!) Specific
          Applications do NOT require auto-assigned, default project
    """
    core_projects = core_application.get_projects(user)
    return core_projects


def _convert_from_instance(esh_driver, provider_uuid, image_id):
    provider_machine = get_or_create_provider_machine(image_id, 'Unknown Image',
            provider_uuid)
    return provider_machine

def compare_core_machines(mach_1, mach_2):
    """
    Comparison puts machines in LATEST start_date, then Lexographical ordering
    """
    if mach_1.application.featured and not mach_2.application.featured:
        return -1
    elif not mach_1.application.featured and mach_2.application.featured:
        return 1
    #Neither/Both images are featured.. Check start_date
    if mach_1.application.start_date > mach_2.application.start_date:
        return -1
    elif mach_1.application.start_date < mach_2.application.start_date:
        return 1
    else:
        return cmp(mach_1.instance_source.identifier, mach_2.instance_source.identifier)

def filter_core_machine(provider_machine):
    """
    Filter conditions:
    * Application does not have an end_date
    * end_date < now
    """
    now = timezone.now()
    #Ignore end dated providers
    if provider_machine.instance_source.end_date or\
       provider_machine.application.end_date:
        if provider_machine.instance_source.end_date:
            return not(provider_machine.instance_source.end_date < now)
        if provider_machine.application.end_date:
            return not(provider_machine.application.end_date < now)
    return True
