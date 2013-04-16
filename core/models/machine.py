"""
  Machine models for atmosphere.
"""
from hashlib import md5

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


from atmosphere.logger import logger

from core.models.script import Package
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
    tags = models.ManyToManyField(Tag)
    icon = models.ImageField(upload_to="machine_images", null=True, blank=True)
    init_package = models.ForeignKey(Package, null=True, blank=True)
    private = models.BooleanField(default=False)
    providers = models.ManyToManyField(Provider, through="ProviderMachine")
    featured = models.BooleanField(default=False)
    created_by = models.ForeignKey(User)  # The user that requested imaging
    start_date = models.DateTimeField(default=timezone.now())
    end_date = models.DateTimeField(null=True, blank=True)

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
                updateTags(self, kwargs[key].split(","))
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
    identifier = models.CharField(max_length=128)  # EMI-12341234

    def icon_url(self):
        return self.machine.icon.url if self.machine.icon else None

    def creator_name(self):
        return self.machine.created_by.username

    def hash_alias(self):
        return md5(self.identifier).hexdigest()

    def find_machine_owner(self):
        if self.provider.location == 'EUCALYPTUS':
            pass  # Parse the XML manifest
        return ""

    def esh_architecture(self):
        return self.esh._image.extra.get('architecture', "N/A")

    def esh_ownerid(self):
        return self.esh._image.extra.get('ownerid', "admin")

    def esh_state(self):
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
    ProviderMachine.cached_machines = {}
    cms = ProviderMachine.objects.all()
    for cm in cms:
        ProviderMachine.cached_machines[(cm.provider.id, cm.identifier)] = cm
    #logger.debug("built core machines dictionary with %s machines." %
    #             len(ProviderMachine.cached_machines))


"""
Useful utility methods for the Core Model..
"""


def findProviderMachine(provider_alias, provider_id):
    if not ProviderMachine.cached_machines:
        build_cached_machines()
    return ProviderMachine.cached_machines.get(
        (int(provider_id), provider_alias))


def loadMachine(machine_name, provider_alias, provider_id):
    """
    Returns List<ProviderMachine>
    Each object contains reference to a new machine-alias combination
    Will create a new machine if one does not exist
    """
    machine = findProviderMachine(provider_alias, provider_id)
    if machine:
        return machine
    else:
        return createProviderMachine(machine_name, provider_alias, provider_id)


def createProviderMachine(machine_name, provider_alias,
                          provider_id, description=None):
    #No Provider Machine.. Time to build one
    provider = Provider.objects.get(id=provider_id)
    logger.debug("Provider %s" % provider)
    machine = getGenericMachine(machine_name)
    logger.debug("Machine %s" % machine)
    if not machine:
        #Build a machine to match
        if not description:
            description = "Describe Machine %s" % provider_alias
        machine = createGenericMachine(machine_name, description)
    provider_machine = ProviderMachine.objects.create(
        machine=machine,
        provider=provider,
        identifier=provider_alias)
    logger.info("New ProviderMachine created: %s" % provider_machine)
    if ProviderMachine.cached_machines:
        ProviderMachine.cached_machines[(
            provider_machine.provider.id,
            provider_machine.identifier)] = provider_machine
    return provider_machine


def getGenericMachine(name):
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


def createGenericMachine(name, description, creator=None):
    if not description:
        description = ""
    if not creator:
        creator = User.objects.get_or_create(username='admin')[0]
    new_mach = Machine.objects.create(name=name,
                                      description=description,
                                      created_by=creator)
    return new_mach


def convertEshMachine(eshMachine, provider_id):
    """
    """
    name = eshMachine.name
    alias = eshMachine.alias
    provider_machine = loadMachine(name, alias, provider_id)
    provider_machine.esh = eshMachine
    return provider_machine
