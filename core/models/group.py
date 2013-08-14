"""
Atmosphere utilizes the DjangoGroup model
to manage users via the membership relationship
"""
# vim: tabstop=2 expandtab shiftwidth=2 softtabstop=2

from django.db import models
from django.contrib.auth.models import Group as DjangoGroup
from django.contrib.auth.models import User as DjangoUser
from core.models.identity import Identity
from core.models.provider import Provider
from core.models.machine import Machine
from core.models.instance import Instance
from core.models.quota import Quota
from core.models.allocation import Allocation


class Group(DjangoGroup):
    """
    Extend the Django Group model to support 'membership'
    """
    leaders = models.ManyToManyField(DjangoUser)
    providers = models.ManyToManyField(Provider, through='ProviderMembership',
        blank=True)
    identities = models.ManyToManyField(Identity, through='IdentityMembership',
        blank=True)
    instances = models.ManyToManyField(Instance, through='InstanceMembership',
        blank=True)
    machines = models.ManyToManyField(Machine, through='MachineMembership',
        blank=True)

    def json(self):
        return {
            'id': self.id,
            'name': self.name
        }

    class Meta:
        db_table = 'group'
        app_label = 'core'


def getUsergroup(username):
    groups = Group.objects.filter(name=username)
    if not groups:
        return None
    return groups[0]


class ProviderMembership(models.Model):
    """
    ProviderMembership allows group 'discovery access'
    to that provider in the API/Frontend.
    IdentityMembership is still required to use the API/Frontend.
    """
    provider = models.ForeignKey(Provider)
    member = models.ForeignKey(Group)

    def __unicode__(self):
        return "%s can use provider %s" % (self.member, self.provider)

    class Meta:
        db_table = 'provider_membership'
        app_label = 'core'


class IdentityMembership(models.Model):
    """
    IdentityMembership allows group 'API access' to use a specific provider
    ProviderMembership is still required to view a provider in the API/UI.
    The identity is given a quota on how many resources can be allocated
    """
    identity = models.ForeignKey(Identity)
    member = models.ForeignKey(Group)
    quota = models.ForeignKey(Quota)
    allocation = models.ForeignKey(Allocation, null=True, blank=True)

    def __unicode__(self):
        return "%s can use identity %s" % (self.member, self.identity)

    class Meta:
        db_table = 'identity_membership'
        app_label = 'core'


class InstanceMembership(models.Model):
    """
    InstanceMembership allows group to see Instances in the frontend/API calls.
    InstanceMembership is the equivilant of
    'sharing' your instance with another Group/User
    Because InstanceMembers will not have that instance's Identity,
    calls to terminate/request imaging/attach/detach *should* fail.
    (This can also be dictated by permission)
    """
    instance = models.ForeignKey(Instance)
    owner = models.ForeignKey(Group)

    def __unicode__(self):
        return "%s is a member-of %s" % (self.owner, self.instance)

    class Meta:
        db_table = 'instance_membership'
        app_label = 'core'


class MachineMembership(models.Model):
    """
    MachineMembership allows group to see Mamchine in the frontend/API calls
    MachineMembership is necessary when a machine has been listed as private
    and allows another Group/User to see and launch the machine.
    (This can also be dictated by permissions)
    """
    machine = models.ForeignKey(Machine)
    owner = models.ForeignKey(Group)

    def __unicode__(self):
        return "%s is a member-of %s" % (self.owner, self.machine)

    class Meta:
        db_table = 'machine_membership'
        app_label = 'core'
