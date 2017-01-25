"""
Service Provider model for atmosphere.
"""

from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.postgres.fields import JSONField

from rtwo.models.provider import EucaProvider, OSProvider
from core.validators import validate_timezone

from uuid import uuid4
from threepio import logger

class PlatformType(models.Model):

    """
    Keep track of Virtualization Platform via type
    """

    name = models.CharField(max_length=256)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)

    def json(self):
        return {
            'name': self.name
        }

    class Meta:
        db_table = 'platform_type'
        app_label = 'core'

    def __unicode__(self):
        return self.name


class ProviderType(models.Model):

    """
    Keep track of Provider via type
    """
    name = models.CharField(max_length=256)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)

    def json(self):
        return {
            'name': self.name
        }

    class Meta:
        db_table = 'provider_type'
        app_label = 'core'

    def __unicode__(self):
        return self.name


class Provider(models.Model):
    """
    Detailed information about a provider
    Providers have a specific location
    (Human readable to describe where/what cloud it is)
    Active providers are "Online",
    Inactive providers are shown as "Offline" in the UI and API requests.
    Start date and end date are recorded for logging purposes
    """
    # CONSTANTS
    ALLOWED_STATES = [
        "Suspend",
        "Stop",
        "Terminate",
        "Shelve", "Shelve Offload"]

    # Fields
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    location = models.CharField(max_length=256)
    description = models.TextField(blank=True)
    type = models.ForeignKey(ProviderType)
    virtualization = models.ForeignKey(PlatformType)
    active = models.BooleanField(default=True)
    # NOTE: we are overloading this variable to stand in for 'allow_imaging'
    public = models.BooleanField(default=False)
    auto_imaging = models.BooleanField(default=False)
    timezone = models.CharField(
        max_length=128,
        validators=[validate_timezone],
        default='America/Phoenix')
    over_allocation_action = models.ForeignKey(
        "InstanceAction", blank=True, null=True)
    cloud_config = JSONField(blank=True, null=True)  # Structure will be tightened up in the future
    cloud_admin = models.ForeignKey("AtmosphereUser", related_name="admin_providers", blank=True, null=True)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(blank=True, null=True)

    def clean(self):
        """
        Don't allow 'non-terminal' InstanceAction
        to be set as over_allocation_action
        """
        over_alloc_action = self.over_allocation_action

        if over_alloc_action and over_alloc_action.name not in Provider.ALLOWED_STATES:
            raise ValidationError(
                "Instance action %s is not in ALLOWED_STATES for "
                "Over allocation action. ALLOWED_STATES=%s" %
                (self.over_allocation_action.name, Provider.ALLOWED_STATES))

    @classmethod
    def get_active(cls, provider_uuid=None, type_name=None):
        """
        Get the provider if it's active, otherwise raise
        Provider.DoesNotExist.
        """
        active_providers = cls.objects.filter(
            Q(end_date=None) | Q(end_date__gt=timezone.now()),
            active=True)
        if type_name:
            active_providers = active_providers.filter(
                type__name__iexact=type_name)
        if provider_uuid:
            # no longer a list
            active_providers = active_providers.get(uuid=provider_uuid)
        return active_providers

    def get_config(self, section, config_key, default_value=None, raise_exc=True):
        try:
            value = self.cloud_config[section][config_key]
        except (KeyError, TypeError):
            logger.error("Cloud config ['%s']['%s'] is missing -- using default value (%s)" % (section, config_key, default_value))
            if not default_value and raise_exc:
                raise Exception("Cloud config ['%s']['%s'] is missing -- no default value provided" % (section, config_key))
            value = default_value
        return value

    def get_esh_credentials(self, esh_provider):
        cred_map = self.get_credentials()
        if isinstance(esh_provider, OSProvider):
            cred_map['ex_force_auth_url'] = cred_map.pop('auth_url','')
            if cred_map.get('ex_force_auth_version','2.0_password') == '2.0_password'\
                    and cred_map['ex_force_auth_url'] and '/v2.0/tokens' not in cred_map['ex_force_auth_url']:
                cred_map['ex_force_auth_url'] += '/v2.0/tokens'

        elif isinstance(esh_provider, EucaProvider):
            ec2_url = cred_map.pop('ec2_url')
            url_map = EucaProvider.parse_url(ec2_url)
            cred_map.update(url_map)
        return cred_map

    def get_total_hours(self, identity):
        if identity.provider != self:
            raise Exception("Provider Mismatch - %s != %s"
                % (self, identity.provider))
        return self.get_total_hours()

    def get_platform_name(self):
        return self.virtualization.name

    def get_type_name(self):
        return self.type.name

    def is_active(self):
        if not self.active:
            return False
        if self.end_date:
            now = timezone.now()
            return not(self.end_date < now)
        return True

    def get_location(self):
        return self.location

    def get_credential(self, key):
        cred = self.providercredential_set.filter(key=key)
        return cred[0].value if cred else None

    def credentials(self):
        return self.providercredential_set.all()

    def get_credentials(self):
        """
        Returns a dict of
        { 'key': 'abc', 'secret': 'xyz' }
        instead of
        [ <Credential: Key=key, Value=abc>, <Credential: Key=secret Value=xyz> ]
        """
        cred_map = {}
        for cred in self.credentials():
            cred_map[cred.key] = cred.value
        return cred_map

    def get_routers(self):
        """
        Using the two kwargs:
        'router_name' and 'public_routers'
        return a list of routers:
        ['router1']
        ['router1','router2,'...]
        """
        public_routers = self.get_credential('public_routers')
        router_name = self.get_credential('router_name')
        if public_routers:
            return public_routers.split(',')
        else:
            return [router_name]

    def select_router(self, router_distribution=None):
        """
        Select and return the router_name with the smallest number of users

        param: router_distribution (Optional) - This dictionary will be used
        in place of `self.get_router_distribution()` allowing you to speed up
        -OR- redistribute all routers evently as part of a batch process.
        (See scripts/admin_redistribute_routers.py)
        """
        if not router_distribution:
            router_distribution = self.get_router_distribution()
        minimum = -1
        minimum_key = None
        for key, count in router_distribution.items():
            if minimum == -1:
                minimum = count
                minimum_key = key
            elif count < minimum:
                minimum = count
                minimum_key = key
        return minimum_key

    def get_router_distribution(self, router_count_map={}):
        """
        Determine the distibution of routers based on:
        * The router names that are stored on the provider
        * The router names that are stored directly on an identity (for this provider)

        """
        router_list = self.get_routers()
        if not router_count_map:
            router_count_map = {rtr: 0 for rtr in router_list}
        query = Q(credential__key='router_name')
        includes_router = self.identity_set.filter(query)
        for entry in includes_router.values_list('credential__value', flat=True):
            if entry in router_count_map:
                router_count_map[entry] = router_count_map[entry] + 1
            else:
                router_count_map[entry] = 1

        for key in router_count_map.keys():
            if key not in router_list:
                logger.info("Skipping unknown router: %s" % key)
                del router_count_map[key]

        logger.info( "Current distribution of routers:")
        for entry, count in router_count_map.items():
            logger.info("%s: %s" % (entry, count))

        return router_count_map

    def missing_routers(self):
        query = Q(credential__key='router_name')
        needs_router = self.identity_set.filter(~query).order_by('created_by__username')
        return needs_router

    def list_users(self):
        """
        Get a list of users from the list of identities found in a provider.
        """
        from core.models.user import AtmosphereUser
        users_on_provider = self.identity_set.values_list(
            'created_by__username',
            flat=True)
        return AtmosphereUser.objects.filter(username__in=users_on_provider)

    def list_admin_names(self):
        return self.accountprovider_set.values_list(
            'identity__created_by__username',
            flat=True)

    @property
    def admin(self):
        all_admins = self.list_admins()
        if all_admins.count():
            return all_admins[0]
        return None

    def list_admins(self):
        from core.models.identity import Identity
        identity_ids = self.accountprovider_set.values_list(
            'identity',
            flat=True)
        return Identity.objects.filter(id__in=identity_ids)

    def get_admin_identity(self):
        provider_admins = self.list_admins()
        if provider_admins:
            return provider_admins[0]
        return None

    def __unicode__(self):
        return "%s:%s" % (self.id, self.location)

    class Meta:
        db_table = 'provider'
        app_label = 'core'


class ProviderConfiguration(models.Model):
    """
    Database-controlled configuration of the provider
    Values changed here will affect how the API processes
    certain requests.
    """
    provider = models.OneToOneField(Provider, primary_key=True, related_name="configuration")
    #TODO: These variables could be migrated from Provider:
    # allow_imaging = models.BooleanField(default=False) # NEW! rather than abusing 'public'
    # auto_imaging = models.BooleanField(default=False)
    # over_allocation_action = models.ForeignKey(
    #     "InstanceAction", blank=True, null=True)

    def __unicode__(self):
        return "Configuration for Provider:%s" % (self.provider)

    class Meta:
        db_table = 'provider_configuration'
        app_label = 'core'


class ProviderInstanceAction(models.Model):
    provider = models.ForeignKey(Provider, related_name='provider_actions')
    instance_action = models.ForeignKey("InstanceAction", related_name='provider_actions')
    #FIXME: enabled could *always* be 'true' when present, and 'false' when not present..
    enabled = models.BooleanField(default=True)

    def __unicode__(self):
        return "Provider:%s Action:%s Enabled:%s" % \
            (self.provider, self.instance_action, self.enabled)

    class Meta:
        db_table = 'provider_instance_action'
        app_label = 'core'
        unique_together = (("provider", "instance_action"),)


class ProviderDNSServerIP(models.Model):

    """
    Used to describe all available
    DNS servers (by IP, sorted by order, then id) for a given provider
    """
    provider = models.ForeignKey(Provider, related_name="dns_server_ips")
    ip_address = models.GenericIPAddressField(null=True, unpack_ipv4=True)
    order = models.IntegerField()

    def __unicode__(self):
        return "#%s Provider:%s ip_address:%s" % \
            (self.order, self.provider, self.ip_address)

    class Meta:
        db_table = 'provider_dns_server_ip'
        app_label = 'core'
        unique_together = (("provider", "ip_address"),
                           ("provider", "order"))


class AccountProvider(models.Model):

    """
    This model is reserved exclusively for accounts that can see everything on
    a given provider.
    This class only applies to Private clouds!
    """
    provider = models.ForeignKey(Provider)
    identity = models.ForeignKey('Identity')

    @classmethod
    def make_superuser(cls, core_group, quota=None):
        from core.models import Quota
        if not quota:
            quota = Quota.max_quota()
        account_providers = AccountProvider.objects.distinct('provider')
        for acct in account_providers:
            acct.share_with(core_group)

    def share_with(self, core_group, quota=None):
        prov_member = self.provider.share(core_group)
        id_member = self.identity.share(core_group, quota=quota)
        return (prov_member, id_member)

    def __unicode__(self):
        return "Account Admin %s for %s" % (self.identity, self.provider)

    class Meta:
        db_table = 'provider_admin'
        app_label = 'core'


# Save Hooks Here:


def get_or_create_provider_configuration(sender, provider_instance=None, created=False, **kwargs):
    if not provider_instance:
        return
    prof = ProviderConfiguration.objects.get_or_create(provider=provider_instance)
    if prof[1] is True:
        logger.debug("Creating Provider Configuration for %s" % provider_instance)

# Instantiate the hooks:
post_save.connect(get_or_create_provider_configuration, sender=Provider)
