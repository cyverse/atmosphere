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
from core.models.version import ApplicationVersion, create_app_version, get_app_version, get_version_for_machine
from core.models.identity import Identity
from core.models.license import License
from core.models.provider import Provider
from core.models.tag import Tag, updateTags
from core.fields import VersionNumberField, VersionNumber

from core.metadata import _get_owner_identity


class ProviderMachine(BaseSource):
    """
    Machines are created by Providers, and multiple providers
    can implement a single machine (I.e. Ubuntu 12.04)
    However each provider will have a specific, unique identifier
    to represent that machine. (emi-12341234 vs ami-43214321)
    """
    esh = None
    application_version = models.ForeignKey(ApplicationVersion, related_name="machines", null=True)

    @property
    def application(self):
        return self.application_version.application

    @property
    def identifier(self):
        return self.instance_source.identifier

    @property
    def name(self):
        return self.application.name

    @classmethod
    def test_existence(cls, provider, identifier):
        """
        Fastest DB Query for existence testing
        """
        return ProviderMachine.objects.filter(instance_source__identifier=identifier, instance_source__provider=provider).count()

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
            image = accounts.get_image(self.identifier)
            accounts.image_manager.update_image(image, **image_updates)
        except Exception as ex:
            logger.exception("Image Update Failed for %s on Provider %s"
                        % (self.identifier, self.instance_source.provider))
            #logger.exception("Image Update Failed for %s on Provider %s"
            #                 % (self.identifier, self.provider))

    def update_version(self, app_version):
        self.application_version = app_version
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


def get_or_create_provider_machine(image_id, machine_name,
                                   provider_uuid, app=None, version=None):
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
        app = get_application(provider_uuid, image_id, machine_name)
    #ASSERT: If no application here, this is a new image (Found on an instance)
    # that was created on a seperate server. We need to make a new one.
    if not app:
        app = create_application(provider_uuid, image_id, machine_name)

    if not version:
        version = get_version_for_machine(provider_uuid, image_id)
    if not version:
        version = create_app_version(app, "1.0")

    return create_provider_machine(image_id, provider_uuid, app, version=version)

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
        image = accounts.get_image(image_id)
        if not image:
            continue
        tenant_id = accounts.get_project(tenant_name).id
        write_app_to_metadata(provider_machine, owner=tenant_id)
        print "App data saved for %s" % image_id
        accounts.image_manager.share_image(image, tenant_name)
        print "Shared access to %s with %s" % (image_id, tenant_name)
        accounts.image_manager.unshare_image(image, old_tenant_name)
        print "Removed access to %s for %s" % (image_id, old_tenant_name)


def provider_machine_update_hook(new_machine, provider_uuid, identifier):
    """
    RULES:
    #1. READ operations ONLY!
    #2. FROM Cloud --> ProviderMachine ONLY!
    """
    from service.openstack import glance_update_machine
    provider = Provider.objects.get(uuid=provider_uuid)
    if provider.get_type_name().lower() == 'openstack':
        glance_update_machine(new_machine)
    else:
        logger.warn("machine data for %s is likely incomplete. Create a new hook for %s." % provider)


def create_provider_machine(identifier, provider_uuid, app,
                            created_by_identity=None, version=None):
    # Attempt to match machine by provider alias
    # Admin identity used until the real owner can be identified.
    provider = Provider.objects.get(uuid=provider_uuid)
    if not created_by_identity:
        created_by_identity = provider.admin

    #TODO: Reminder to re-evaluate these lines when you get to Django 1.8
    source = InstanceSource.objects.create(
        identifier=identifier,
        created_by=created_by_identity.created_by,
        provider=provider,
        created_by_identity=created_by_identity,
    )
    if not version:
        version = create_app_version(app)
    logger.debug("Provider %s" % provider)
    logger.debug("App %s" % app)
    logger.debug("Version %s" % version)
    provider_machine = ProviderMachine.objects.create(
        instance_source=source,
        application_version=version,
    )
    provider_machine_update_hook(provider_machine, provider_uuid, identifier)
    logger.info("New ProviderMachine created: %s" % provider_machine)
    add_to_cache(provider_machine)
    return provider_machine


def _username_lookup(provider_uuid, username):
    try:
        return Identity.objects.get(
            provider__uuid=provider_uuid,
            created_by__username=username)
    except Identity.DoesNotExist:
        return None


def update_provider_machine(provider_machine, new_created_by_identity=None, new_created_by=None, new_application_version=None):
    """
    Used to explicitly 'update' + call the 'provider_machine_write_hook'
    * Glance updates, metadata updates, etc.
    *
    TODO: Find a way to bring this IN to ProviderMachine.save?
    """
    if new_created_by:
        provider_machine.created_by = new_created_by
    if new_created_by_identity:
        provider_machine.created_by_identity = new_created_by_identity
    if new_application_version:
        provider_machine.application_version = new_version
        provider_machine.application = new_version.application
    provider_machine.save()
    provider_machine_write_hook(provider_machine)


def provider_machine_write_hook(provider_machine):
    """
    RULES:
    #1. WRITE operations ONLY!
    #2. FROM ProviderMachine --> Cloud ONLY!
    """
    from service.openstack import glance_write_machine
    provider = provider_machine.instance_source.provider
    if provider.get_type_name().lower() == 'openstack':
        glance_write_machine(provider_machine)
    else:
        logger.warn("Create a new write hook for %s to keep cloud objects up to date." % provider)



def add_to_cache(provider_machine):
    #ProviderMachine.cached_machines[(
    #    provider_machine.provider.id,
    #    provider_machine.identifier)] = provider_machine
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
    alias = esh_machine.id
    app = get_application(provider_uuid, alias, name)
    if not app:
        logger.debug("Creating Application for Image %s" % (alias, ))
        app = create_application(provider_uuid, alias, name)

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
    provider_machine = get_or_create_provider_machine(image_id, 'Imported Machine %s' % image_id,
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
