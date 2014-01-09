"""
  Machine models for atmosphere.
"""
import json
from hashlib import md5

from django.db import models
from django.utils import timezone
from threepio import logger

from core.models.identity import Identity
from core.models.provider import Provider
from core.models.tag import Tag, updateTags


class Machine(models.Model):
    """
    Machines are described with their name, tags, and a lengthy description
    of what is included in the machine.
    A machine has an icon/logo for use in frontend applications
    On launch, new instances will request an init_package
    to run additional runtime configuration scripts.
    Private machines can be 'shared' with other groups
    using MachineMembership (see group.py)
    Machines creation and deletion date,
    as well as the user who created the machine,
    are recorded for logging purposes.
    """
    name = models.CharField(max_length=256)
    description = models.TextField(null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True)
    icon = models.ImageField(upload_to="machine_images", null=True, blank=True)
    private = models.BooleanField(default=False)
    providers = models.ManyToManyField(Provider, through="ProviderMachine",
            blank=True)
    featured = models.BooleanField(default=False)
    created_by = models.ForeignKey('AtmosphereUser')  # The user that requested imaging
    created_by_identity = models.ForeignKey(Identity, null=True)
    start_date = models.DateTimeField(default=timezone.now())
    end_date = models.DateTimeField(null=True, blank=True)
    application = models.ForeignKey('Application', null=True)

    def update(self, *args, **kwargs):
        """
        Allows for partial updating of the model
        """
        #Upload args into kwargs
        for arg in args:
            for (key, value) in arg.items():
                kwargs[key] = value
        #Update the values
        for key in kwargs.keys():
            if key == 'tags':
                if type(kwargs[key]) != list:
                    tags_list = kwargs[key].split(",")
                else:
                    tags_list = kwargs[key]
                updateTags(self, tags_list)
                continue
            setattr(self, key, kwargs[key])
        self.save()
        return self

    def json(self):
        return {
            'name': self.name,
            'description': self.description,
            'tags': [tag.json() for tag in self.tags.all()],
            'icon': self.icon.url if self.icon else '',
            'private': self.private,
            'owner': self.created_by.username if self.created_by else "",
        }

    def __unicode__(self):
        return "%s" % (self.name,)

    class Meta:
        db_table = "machine"
        app_label = "core"


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
    machine = models.ForeignKey(Machine)
    identifier = models.CharField(max_length=256, unique=True)  # EMI-12341234
    created_by = models.ForeignKey('AtmosphereUser', null=True)
    created_by_identity = models.ForeignKey(Identity, null=True)
    start_date = models.DateTimeField(default=timezone.now())
    end_date = models.DateTimeField(null=True, blank=True)

    def icon_url(self):
        return self.machine.icon.url if self.machine.icon else None

    def creator_name(self):
        if self.machine:
            return self.machine.created_by.username
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

    def json(self):
        return {
            'alias': self.identifier,
            'alias_hash': self.hash_alias(),
            'machine': self.machine,
            'provider': self.provider,
        }

    def __unicode__(self):
        return "%s (Provider:%s - Machine:%s) " %\
            (self.identifier, self.provider, self.machine)

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


def load_machine(provider_alias, machine_name, provider_id):
    """
    Returns ProviderMachine
    """
    return create_provider_machine(machine_name, provider_alias, provider_id)

def update_machine_owner(machine, identity):
    machine.created_by_identity=identity
    machine.created_by=identity.created_by
    machine.save()


def create_provider_machine(machine_name, provider_alias,
                          provider_id, description=None):
    #Attempt to match machine by provider alias
    provider_machine = get_provider_machine(identifier=provider_alias)
    if provider_machine:
        return provider_machine

    #Admin identity used until the real owner can be identified.
    provider = Provider.objects.get(id=provider_id)
    machine_owner = provider.get_admin_identity()
    #Machines with an exact name match are treated as 'identical'
    machine = get_generic_machine(machine_name)
    if not machine:
        #Build a machine
        if not description:
            description = "%s" % machine_name
        machine = create_generic_machine(machine_name, description, machine_owner)
    logger.debug("Provider %s" % provider)
    logger.debug("Machine %s" % machine)
    provider_machine = ProviderMachine.objects.create(
        machine=machine,
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

def get_generic_machine(name):
    try:
        machine = Machine.objects.get(name=name)
        return machine
    except Machine.DoesNotExist:
        return None
    except Machine.MultipleObjectsReturned:
        return Machine.objects.filter(name=name)[0]
    except Exception, e:
        logger.error(e)
        logger.error(type(e))


def create_generic_machine(name, description, creator_id=None):
    from core.models import AtmosphereUser
    if not description:
        description = ""
    if not creator_id:
        creator_id = AtmosphereUser.objects.get_or_create(username='admin')[0]
    new_mach = Machine.objects.create(name=name,
                                      description=description,
                                      created_by=creator_id.created_by,
                                      created_by_identity=creator_id)
    return new_mach


def convert_esh_machine(esh_driver, esh_machine, provider_id, image_id=None):
    """
    """
    if image_id and not esh_machine:
        provider_machine = load_machine(image_id, 'Unknown Image', provider_id)
        return provider_machine
    elif not esh_machine:
        return None
    name = esh_machine.name
    alias = esh_machine.alias
    provider_machine = load_machine(alias, name, provider_id)
    provider_machine.esh = esh_machine
    provider_machine = set_machine_from_metadata(esh_driver, provider_machine)
    return provider_machine


def compare_core_machines(mach_1, mach_2):
    """
    Comparison puts machines in LATEST start_date, then Lexographical ordering
    """
    if mach_1.machine.featured and not mach_2.machine.featured:
        return -1
    elif not mach_1.machine.featured and mach_2.machine.featured:
        return 1
    #Neither/Both images are featured.. Check start_date
    if mach_1.machine.start_date > mach_2.machine.start_date:
        return -1
    elif mach_1.machine.start_date < mach_2.machine.start_date:
        return 1
    else:
        return cmp(mach_1.identifier, mach_2.identifier)

def filter_core_machine(provider_machine):
    """
    Filter conditions:
    * Machine does not have an end_date
    * end_date < now
    """
    now = timezone.now()
    if provider_machine.end_date or\
       provider_machine.machine.end_date:
        if provider_machine.end_date:
            return not(provider_machine.end_date < now)
        if provider_machine.machine.end_date:
            return not(provider_machine.machine.end_date < now)
    return True


def set_machine_from_metadata(esh_driver, core_machine):
    #Fixes Dep. loop - Do not remove
    from api.serializers import ProviderMachineSerializer
    if not hasattr(esh_driver._connection, 'ex_get_image_metadata'):
        #NOTE: This can get chatty, only uncomment for debugging
        #Breakout for drivers (Eucalyptus) that don't support metadata
        #logger.debug("EshDriver %s does not have function 'ex_get_image_metadata'"
        #            % esh_driver._connection.__class__)
        return core_machine
    esh_machine = core_machine.esh
    try:
        metadata =  esh_driver._connection.ex_get_image_metadata(esh_machine)
    except Exception:
        logger.warn('Warning: Metadata could not be retrieved for: %s' % esh_machine)
        return core_machine

    #TAGS must be converted from String --> List
    if 'tags' in metadata and type(metadata['tags']) != list:
        tags_as_list = metadata['tags'].split(', ')
        metadata['tags'] = tags_as_list
    serializer = ProviderMachineSerializer(core_machine, data=metadata, partial=True)
    if not serializer.is_valid():
        logger.info("New metadata failed: %s" % metadata)
        logger.warn("Encountered errors serializing metadata:%s"
                    % serializer.errors)
        return core_machine
    serializer.save()
    # Retrieve and prepare the new obj
    core_machine = serializer.object
    if 'tags' in metadata:
        updateTags(core_machine.machine, metadata['tags'])
        core_machine.machine.save()
    core_machine.esh = esh_machine
    return core_machine

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
        #TAGS must be converted from list --> String
        if 'tags' in data and type(data['tags']) == list:
            data['tags'] = json.dumps(data['tags'])
        logger.info("New metadata:%s" % data)
        return esh_driver._connection.ex_set_image_metadata(esh_machine, data)
    except Exception, e:
        if 'incapable of performing the request' in e.message:
            return {}
        else:
            raise

