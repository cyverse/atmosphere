"""
  Machine models for atmosphere.
"""
import json
from hashlib import md5
from uuid import uuid5, UUID

from django.db import models
from django.utils import timezone
from threepio import logger

from atmosphere import settings
from core.models.application import Application
from core.models.identity import Identity
from core.models.provider import Provider

from core.models.tag import Tag, updateTags
from core.fields import VersionNumberField, VersionNumber

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

    identifier = models.CharField(max_length=256, unique=True)  # EMI-12341234
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


def load_provider_machine(provider_alias, machine_name,
                          provider_id):
    """
    Returns ProviderMachine
    """
    provider_machine = get_provider_machine(identifier=provider_alias)
    if provider_machine:
        return provider_machine

    return create_provider_machine(machine_name, provider_alias,
                                   provider_id)

def update_machine_owner(machine, identity):
    machine.created_by_identity=identity
    machine.created_by=identity.created_by
    machine.save()


def create_provider_machine(machine_name, provider_alias,
                          provider_id, description=None):
    #Attempt to match machine by provider alias
    #Admin identity used until the real owner can be identified.
    provider = Provider.objects.get(id=provider_id)
    machine_owner = provider.get_admin_identity()

    app = get_application(provider_alias)
    #TODO: Use metadata to replace application details
    if not app:
        #Build a app
        if not description:
            description = "%s" % machine_name
        app = create_application(machine_name, description, machine_owner, provider_alias)
    logger.debug("Provider %s" % provider)
    logger.debug("App %s" % app)
    provider_machine = ProviderMachine.objects.create(
        application=app,
        provider=provider,
        created_by=machine_owner.created_by,
        created_by_identity=machine_owner,
        identifier=provider_alias)
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

def get_provider_machine(identifier):
    try:
        machine = ProviderMachine.objects.get(identifier=identifier)
        return machine
    except ProviderMachine.DoesNotExist:
        return None

def get_application(identifier):
    app_uuid = uuid5(settings.ATMOSPHERE_NAMESPACE_UUID, str(identifier))
    app_uuid = str(app_uuid)
    try:
        app = Application.objects.get(uuid=app_uuid)
        return app
    except Application.DoesNotExist:
        return None
    except Exception, e:
        logger.error(e)
        logger.error(type(e))


def create_application(name, description, creator_identity, identifier):
    from core.models import AtmosphereUser
    if not description:
        description = ""
    app_uuid = uuid5(settings.ATMOSPHERE_NAMESPACE_UUID, str(identifier))
    app_uuid = str(app_uuid)
    new_mach = Application.objects.create(
            name=name,
            description=description,
            created_by=creator_identity.created_by,
            created_by_identity=creator_identity,
            uuid=app_uuid)
    return new_mach


def convert_esh_machine(esh_driver, esh_machine, provider_id, image_id=None):
    """
    Takes as input an (rtwo) driver and machine, and a core provider id
    Returns as output a core ProviderMachine
    """
    if image_id and not esh_machine:
        return _convert_from_instance(esh_driver, provider_id, image_id)
    elif not esh_machine:
        return None
    metadata = _get_machine_metadata(esh_driver, esh_machine)
    name = esh_machine.name
    alias = esh_machine.alias
    provider_machine = load_provider_machine(alias, name, provider_id)
    #Metadata to parse/use:
    # APP: application_name
    # APP: application_uuid
    # PM : version_id
    # APP: tags
    # Did things change? save it.
    if 'tags' in metadata and type(metadata['tags']) != list:
        tags_as_list = metadata['tags'].split(', ')
        metadata['tags'] = tags_as_list
    # PM : description
    provider_machine.esh = esh_machine
    return provider_machine


def _convert_from_instance(esh_driver, provider_id, image_id):
    provider_machine = load_provider_machine(image_id, 'Unknown Image', provider_id)
    return provider_machine

def _get_machine_metadata(esh_driver, esh_machine):
    if not hasattr(esh_driver._connection, 'ex_get_image_metadata'):
        #NOTE: This can get chatty, only uncomment for debugging
        #Breakout for drivers (Eucalyptus) that don't support metadata
        #logger.debug("EshDriver %s does not have function 'ex_get_image_metadata'"
        #            % esh_driver._connection.__class__)
        return {}
    try:
        metadata =  esh_driver._connection.ex_get_image_metadata(esh_machine)
        return metadata
    except Exception:
        logger.exception('Warning: Metadata could not be retrieved for: %s' % esh_machine)
        return {}

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



def update_machine_metadata(esh_driver, esh_machine, data={}):
    """
    NOTE: This will NOT WORK for TAGS until openstack
    allows JSONArrays as values for metadata!
    """
    if not hasattr(esh_driver._connection, 'ex_set_image_metadata'):
        logger.info("EshDriver %s does not have function 'ex_set_image_metadata'"
                    % esh_driver._connection.__class__)
        return {}
    try:
        # Possible metadata that could be in 'data'
        #  * application uuid
        #  * application name
        #  * specific machine version
        #TAGS must be converted from list --> String
        if 'tags' in data and type(data['tags']) == list:
            data['tags'] = json.dumps(data['tags'])
        logger.info("New metadata:%s" % data)
        return esh_driver._connection.ex_set_image_metadata(esh_machine, data)
    except Exception, e:
        logger.exception("Error updating machine metadata")
        if 'incapable of performing the request' in e.message:
            return {}
        else:
            raise


def update_core_machine_metadata(esh_driver, provider_machine):
    """
    """
    #NOTES: 
    # Dep loop if raised any higher..
    # This function is temporary..
    from api import get_esh_driver
    account_providers = provider_machine.provider.accountprovider_set.all()
    if not account_providers:
        raise Exception("The driver of the account provider is required to"
                        " update image metadata")
    account_provider = account_providers[0].identity
    esh_driver = get_esh_driver(account_provider)
    esh_machine = esh_driver.get_machine(provider_machine.identifier)
    mach_data = {
        "application_uuid":provider_machine.application.uuid,
        "application_name":provider_machine.application.name,
        "application_version":"1.0.0", # REPLACEWITH: provider_machine.version,
        #"tags":[tag for tag in provider_machine.application.tags.all()],
        "description":provider_machine.application.description,
    }
    return update_machine_metadata(esh_driver, esh_machine, mach_data)
