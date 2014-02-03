"""
  Machine models for atmosphere.
"""
import json
from hashlib import md5

from django.db import models
from django.utils import timezone
from threepio import logger

from atmosphere import settings
from core.models.application import Application
from core.models.application import create_application, get_application
from core.models.identity import Identity
from core.models.provider import Provider

from core.models.tag import Tag, updateTags
from core.fields import VersionNumberField, VersionNumber

from core.metadata import _get_owner_identity
from core.application import write_app_data, has_app_data, get_app_data

class ProviderMachine(models.Model):
    """
    Machines are created by Providers, and multiple providers
    can implement a single machine (I.e. Ubuntu 12.04)
    However each provider will have a specific, unique identifier
    to represent that machine. (emi-12341234 vs ami-43214321)
    """
    #Field is Filled out at runtime.. after converting an eshMachine
    esh = None
    cached_machines = None
    provider = models.ForeignKey(Provider)
    application = models.ForeignKey(Application)

    identifier = models.CharField(max_length=256)  # EMI-12341234
    created_by = models.ForeignKey('AtmosphereUser', null=True)
    created_by_identity = models.ForeignKey(Identity, null=True)
    start_date = models.DateTimeField(default=timezone.now())
    end_date = models.DateTimeField(null=True, blank=True)
    version = VersionNumberField(default=int(VersionNumber(1,)))

    def icon_url(self):
        return self.application.icon.url if self.application.icon else None

    def creator_name(self):
        if self.application:
            return self.application.created_by.username
        else:
            return "Unknown"

    def hash_alias(self):
        return md5(self.identifier).hexdigest()

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
           and self.esh._image.extra:
            return self.esh._image.extra.get('ownerid', "admin")

    def esh_state(self):
        if self.esh and self.esh._image\
           and self.esh._image.extra:
            return self.esh._image.extra['state']

    def __unicode__(self):
        return "%s (Provider:%s - App:%s) " %\
            (self.identifier, self.provider, self.application)

    class Meta:
        db_table = "provider_machine"
        app_label = "core"


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


def load_provider_machine(provider_alias, machine_name, provider_id,
                          app=None, metadata={}):
    """
    Returns ProviderMachine
    """
    provider_machine = get_provider_machine(provider_alias, provider_id)
    if provider_machine:
        return provider_machine
    if not app:
        app = get_application(provider_alias, app_uuid=metadata.get('uuid'))
    if not app:
        app = create_application(provider_alias, provider_id, machine_name)
    return create_provider_machine(machine_name, provider_alias, provider_id, app=app, metadata=metadata)

def update_application_owner(application, identity):
    application.created_by_identity=identity
    application.created_by=identity.created_by
    #PUSH METADATA
    application.save()



def create_provider_machine(machine_name, provider_alias, provider_id, app, metadata={}):
    #Attempt to match machine by provider alias
    #Admin identity used until the real owner can be identified.
    provider = Provider.objects.get(id=provider_id)

    #TODO: Read admin owner from location IFF eucalyptus
    machine_owner = _get_owner_identity(metadata.get('owner',''), provider_id)

    logger.debug("Provider %s" % provider)
    logger.debug("App %s" % app)
    provider_machine = ProviderMachine.objects.create(
        application = app,
        provider = provider,
        created_by = machine_owner.created_by,
        created_by_identity = machine_owner,
        identifier = provider_alias,
        version = VersionNumber.string_to_version(
            metadata.get('version','1.0')))
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


def get_provider_machine(identifier, provider_id):
    try:
        machine = ProviderMachine.objects.get(provider__id=provider_id, identifier=identifier)
        return machine
    except ProviderMachine.DoesNotExist:
        return None


def convert_esh_machine(esh_driver, esh_machine, provider_id, image_id=None):
    """
    Takes as input an (rtwo) driver and machine, and a core provider id
    Returns as output a core ProviderMachine
    """
    if image_id and not esh_machine:
        return _convert_from_instance(esh_driver, provider_id, image_id)
    elif not esh_machine:
        return None
    push_metadata = False
    metadata = esh_machine._image.extra.get('metadata',{})
    name = esh_machine.name
    alias = esh_machine.alias
    if metadata and has_app_data(metadata):
        #USE CASE: Application data exists on the image
        # and may exist on this DB
        app = get_application(alias, metadata.get('application_uuid'))
        if not app:
            app_kwargs = get_app_data(metadata, provider_id)
            logger.debug("Creating Application for Image %s "
                         "(Based on Application data: %s)"
                         % (alias, app_kwargs))
            app = create_application(alias, provider_id, **app_kwargs)
    else:
        #USE CASE: Application data does NOT exist,
        # This machine is assumed to be its own application, so run the
        # machine alias to retrieve any existing application.
        # otherwise create a new application with the same name as the machine
        # App assumes all default values
        #logger.info("Image %s missing Application data" % (alias, ))
        push_metadata = True
        #TODO: Get application 'name' instead?
        app = get_application(alias)
        if not app:
            logger.debug("Creating Application for Image %s" % (alias, ))
            app = create_application(alias, provider_id, name)
    provider_machine = load_provider_machine(alias, name, provider_id,
                                             app=app, metadata=metadata)
    if push_metadata and hasattr(esh_driver._connection,
                                 'ex_set_image_metadata'):
        logger.debug("Creating App data for Image %s:%s" % (alias, app.name))
        write_app_data(esh_driver, provider_machine)
    provider_machine.esh = esh_machine
    return provider_machine


def _convert_from_instance(esh_driver, provider_id, image_id):
    provider_machine = load_provider_machine(image_id, 'Unknown Image', provider_id)
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
        return cmp(mach_1.identifier, mach_2.identifier)

def filter_core_machine(provider_machine):
    """
    Filter conditions:
    * Application does not have an end_date
    * end_date < now
    """
    now = timezone.now()
    if provider_machine.end_date or\
       provider_machine.application.end_date:
        if provider_machine.end_date:
            return not(provider_machine.end_date < now)
        if provider_machine.application.end_date:
            return not(provider_machine.application.end_date < now)
    return True
