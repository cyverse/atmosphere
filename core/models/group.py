"""
Atmosphere utilizes the DjangoGroup model
to manage users via the membership relationship
"""
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from math import floor, ceil

from django.db import models
from django.contrib.auth.models import Group as DjangoGroup

from threepio import logger

from core.models.allocation import Allocation
from core.models.application import Application
from core.models.identity import Identity
from core.models.provider import Provider
from core.models.quota import Quota
from core.models.user import AtmosphereUser


class Group(DjangoGroup):
    """
    Extend the Django Group model to support 'membership'
    """
    leaders = models.ManyToManyField('AtmosphereUser', through='Leadership')
    providers = models.ManyToManyField(Provider, through='ProviderMembership',
                                       blank=True)
    identities = models.ManyToManyField(Identity, through='IdentityMembership',
                                        blank=True)
    instances = models.ManyToManyField('Instance',
                                       through='InstanceMembership',
                                       blank=True)
    applications = models.ManyToManyField(Application,
                                          related_name='members',
                                          through='ApplicationMembership',
                                          blank=True)
    provider_machines = models.ManyToManyField('ProviderMachine',
                                          related_name='members',
                                          through='ProviderMachineMembership',
                                          blank=True)

    @classmethod
    def create_usergroup(cls, username):
        user = AtmosphereUser.objects.get_or_create(username=username)[0]
        group = Group.objects.get_or_create(name=username)[0]
        if group not in user.groups.all():
            user.groups.add(group)
            user.save()
        l = Leadership.objects.get_or_create(user=user, group=group)[0]
        return (user, group)

    def json(self):
        return {
            'id': self.id,
            'name': self.name
        }

    class Meta:
        db_table = 'group'
        app_label = 'core'


class Leadership(models.Model):
    user = models.ForeignKey('AtmosphereUser')
    group = models.ForeignKey(Group)

    class Meta:
        db_table = 'group_leaders'
        app_label = 'core'


def get_user_group(username):
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

    @classmethod
    def get_membership_for(cls, groupname):

        from core.models import ProviderMembership, Group
        try:
            group = Group.objects.get(name=groupname)
        except Group.DoesNotExist:
            logger.warn("Group %s does not exist" % groupname)
            return None
        provider_members = ProviderMembership.objects.filter(
            member__name=groupname)
        if not provider_members:
            logger.warn("%s is not a member of any provider" % groupname)
        for pm in provider_members:
            identities = IdentityMembership.objects.filter(
                member=group,
                identity__provider=pm.provider)
            if identities:
                return identities[0]
        logger.warn("%s is not a member of any identities" % groupname)
        return None

    def get_allocation_dict(self):
        if not self.allocation:
            return {}
        #Don't move it up. Circular reference.
        from service.allocation import get_time, get_burn_time,\
            delta_to_minutes, delta_to_hours, get_delta
        delta = get_delta(self, time_period=relativedelta(day=1, months=1))
        time_used = get_time(self.identity.created_by,
                             self.identity.id,
                             delta)
        burn_time = get_burn_time(self.identity.created_by, self.identity.id,
                                  delta,
                                  timedelta(minutes=self.allocation.threshold))
        mins_consumed = delta_to_minutes(time_used)
        if burn_time:
            burn_time = delta_to_hours(burn_time)
        allocation_dict = {
            "threshold": floor(self.allocation.threshold/60),
            "current": floor(mins_consumed/60),
            "delta": ceil(delta.total_seconds()/60),
            "burn": burn_time,
            "ttz": (self.allocation.threshold - mins_consumed)/60}
        return allocation_dict

    def get_quota_dict(self):
        quota = self.quota
        quota_dict = {
            "mem": quota.memory,
            "cpu": quota.cpu,
            "storage": quota.storage,
            "storage_count": quota.storage_count,
            "suspended_count": quota.suspended_count,
        }
        return quota_dict

    def save(self, *args, **kwargs):
        """
        Whenever an IdentityMembership changes, update the provider
        specific quota too.
        """
        super(IdentityMembership, self).save(*args, **kwargs)
        try:
            from service.quota import set_provider_quota
            set_provider_quota(self.identity.id)
        except Exception as ex:
            logger.warn("Unable to update service.quota.set_provider_quota.")
            #raise

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
    instance = models.ForeignKey('Instance')
    owner = models.ForeignKey(Group)

    def __unicode__(self):
        return "%s is a member-of %s" % (self.owner, self.instance)

    class Meta:
        db_table = 'instance_membership'
        app_label = 'core'


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
