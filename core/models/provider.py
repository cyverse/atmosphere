"""
Service Provider model for atmosphere.
"""

from django.db import models
from django.utils import timezone

from rtwo.provider import AWSProvider, EucaProvider, OSProvider
from rtwo.provider import Provider as EshProvider
from threepio import logger

class PlatformType(models.Model):
    """
    Keep track of Virtualization Platform via type
    """
    name = models.CharField(max_length=256)
    start_date = models.DateTimeField(default=timezone.now())
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
    start_date = models.DateTimeField(default=timezone.now())
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


class ProviderSize(models.Model):
    #TODO: :Fix the providersize model to have a foreign key to Provider..
    """
    ProviderSize contains the exact amount of resources
    in combination with am chine to launch an instance.
    The alias' are different for each provider and the information necessary
    in each size depends on the provider.
    The current model includes CPU Units/RAM (In GB)/HDD Space (In GB)
    Start date and end date are recorded for logging purposes

    Optional fields include:
      Bandwidth
      Price
    """
    #Special field that is filled out when converting an eshSize
    esh = None
    name = models.CharField(max_length=256)  # Medium Instance
    alias = models.CharField(max_length=256)  # m1.medium
    cpu = models.IntegerField(null=True, blank=True)
    ram = models.IntegerField(null=True, blank=True)
    disk = models.IntegerField(null=True, blank=True)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'provider_size'
        app_label = 'core'


class Provider(models.Model):
    """
    Detailed information about a provider
    Providers have a specific location
    (Human readable to describe where/what cloud it is)
    Active providers are "Online",
    Inactive providers are shown as "Offline" in the UI and API requests.
    Start date and end date are recorded for logging purposes
    """
    location = models.CharField(max_length=256)
    type = models.ForeignKey(ProviderType)
    virtualization = models.ForeignKey(PlatformType)
    active = models.BooleanField(default=True)
    public = models.BooleanField(default=False)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(blank=True, null=True)

    def share(self, core_group):
        """
        """
        from core.models import IdentityMembership, ProviderMembership
        #Does this group already have membership?
        existing_membership = ProviderMembership.objects.filter(
                member=core_group, provider=self)
        if existing_membership:
            return existing_membership[0]
        #Create new membership for this group
        new_membership = ProviderMembership.objects.get_or_create(
                member=core_group, provider=self)
        return new_membership[0]

    def unshare(self, core_group):
        """
        """
        from core.models import IdentityMembership, ProviderMembership
        identity_memberships = IdentityMembership.objects.filter(
                member=core_group, identity__provider=self)
        if identity_memberships:
            raise Exception("Cannot unshare provider membership until all"
                            " Identities on that provider have been removed")
        existing_membership = ProviderMembership.objects.filter(member=core_group, provider=self)
        if existing_membership:
            existing_membership[0].delete()

    def get_membership(self):
        provider_members = self.providermembership_set.all()
        group_names = [prov_member.member for prov_member in provider_members]
        #TODO: Add 'rules' if we want to hide specific users (staff, etc.)
        return group_names

    def get_esh_credentials(self, esh_provider):

        cred_map = self.get_credentials()
        if isinstance(esh_provider, OSProvider):
            cred_map['ex_force_auth_url'] = cred_map.pop('auth_url')
        elif isinstance(esh_provider, EucaProvider):
            ec2_url = cred_map.pop('ec2_url')
            url_map = EucaProvider.parse_url(ec2_url)
            cred_map.update(url_map)
        return cred_map

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

    def get_credentials(self):
        cred_map = {}
        for cred in self.providercredential_set.all():
            cred_map[cred.key] = cred.value
        return cred_map

    def list_admins(self):
        return [admin.identity for admin in self.accountprovider_set.all()]

    def list_admin_names(self):
        return [admin.identity.created_by.username for admin in self.accountprovider_set.all()]

    def get_admin_identity(self):
        provider_admins = self.list_admins()
        if provider_admins:
          return provider_admins[0]
        #TODO: Rely on the account provider instead
        #NOTE: Marked for removal
        from core.models import Identity
        from core.models import AtmosphereUser as User
        from atmosphere.settings import secrets
        if self.location.lower() == 'openstack':
            admin = User.objects.get(username=secrets.OPENSTACK_ADMIN_KEY)
        elif self.location.lower() == 'eucalyptus':
            admin = User.objects.get(username='admin')
        else:
            raise Exception("Could not find admin user for provider %s" % self)

        return Identity.objects.get(provider=self, created_by=admin)

    def __unicode__(self):
        return "%s:%s" % (self.id, self.location)

    class Meta:
        db_table = 'provider'
        app_label = 'core'

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

