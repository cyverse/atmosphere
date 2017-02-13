# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
"""
Atmosphere utilizes the DjangoGroup model
to manage users via the membership relationship
"""
import uuid
from math import floor, ceil

from django.db import models
from django.db.models.signals import post_save
from django.utils import timezone
from django.utils.timezone import datetime, timedelta
from django.contrib.auth.models import Group as DjangoGroup

from threepio import logger

from core.models.allocation_strategy import Allocation
from core.models.application import Application
from core.models.identity import Identity
from core.models.provider import Provider
from core.models.quota import Quota
from core.models.user import AtmosphereUser

from core.query import (
        only_active_memberships, only_active_provider, only_current_provider
    )

class Group(DjangoGroup):

    """
    Extend the Django Group model to support 'membership'
    """
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    leaders = models.ManyToManyField('AtmosphereUser', through='Leadership')
    identities = models.ManyToManyField(Identity, through='IdentityMembership',
                                        blank=True)
    instances = models.ManyToManyField('Instance',
                                       through='InstanceMembership',
                                       blank=True)
    applications = models.ManyToManyField(Application,
                                          related_name='members',
                                          through='ApplicationMembership',
                                          blank=True)
    provider_machines = models.ManyToManyField(
        'ProviderMachine',
        related_name='members',
        through='ProviderMachineMembership',
        blank=True)

    def is_leader(self, test_user):
        return any(user for user in self.leaders.all() if user == test_user)

    @property
    def identitymembership_set(self):
        logger.warn("WARNING - THIS FIELD DEPRECATED for `identity_memberships` REPLACE THE REFERENCE USING THIS LINE")
        return self.identity_memberships

    @property
    def current_identity_memberships(self):
        return self.identity_memberships.filter(only_active_memberships())

    @property
    def current_identities(self):
        identity_ids = self.identity_memberships.filter(
                only_active_memberships()).values_list('identity',flat=True)
        return Identity.objects.filter(only_current_provider(), only_active_provider(), id__in=identity_ids)

    @property
    def current_providers(self):
        provider_ids = self.identity_memberships.filter(
                only_active_memberships()).values_list('identity__provider',flat=True)
        return Provider.objects.filter(id__in=provider_ids)

    @classmethod
    def check_membership(cls, test_user, membership_groups):
        """
        PARAMS:
          test_user - DjangoUser to be tested
          membership_groups - List of groups allowed membership to... Something.
        RETURNS:
          True/False - If any of the users groups grants membership access.
        """
        return any(group for group
                   in test_user.group_set.all() if group in membership_groups)

    @classmethod
    def check_access(cls, user, groupname):
        try:
            if not isinstance(user, AtmosphereUser):
                user = AtmosphereUser.objects.get(username=user.username)
            group = Group.objects.get(name=groupname)
            return user in group.user_set.all()
        except Group.DoesNotExist:
            return False

    @classmethod
    def create_usergroup(cls, username, group_name=None):
        # TODO: ENFORCEMENT of lowercase-only usernames until cleared by mgmt.
        username = username.lower()
        if not group_name:
            group_name = username
        user = AtmosphereUser.objects.get_or_create(username=username)[0]
        group = Group.objects.get_or_create(name=group_name)[0]
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
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
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


class IdentityMembership(models.Model):

    """
    IdentityMembership allows group 'API access' to use a specific provider
    The identity is given a quota on how many resources can be allocated
    """
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    identity = models.ForeignKey(Identity, related_name='identity_memberships')
    member = models.ForeignKey(Group, related_name='identity_memberships')
    allocation = models.ForeignKey(Allocation, null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)

    @classmethod
    def get_membership_for(cls, groupname):
        try:
            group = Group.objects.get(name=groupname)
        except Group.DoesNotExist:
            logger.warn("Group %s does not exist" % groupname)
        try:
            return group.current_identity_memberships.first()
        except IdentityMembership.DoesNotExist:
            logger.warn("%s is not a member of any identities" % groupname)

    @property
    def quota(self):
        return self.identity.quota

    def is_active(self):
        if not self.active:
            return False
        if self.end_date:
            now = timezone.now()
            return not(self.end_date < now)
        return True

    def get_allocation_dict(self):
        if not self.allocation:
            return {}
        # Don't move it up. Circular reference.
        from django.conf import settings
        from service.monitoring import get_delta, _get_allocation_result
        delta = get_delta(self, time_period=settings.FIXED_WINDOW)
        allocation_result = _get_allocation_result(self.identity)
        over_allocation, diff_amount = allocation_result.total_difference()
        burn_time = allocation_result.get_burn_rate()
        # Moving from seconds to hours
        hourly_credit = int(allocation_result
                            .total_credit().total_seconds() / 3600.0)
        hourly_runtime = int(allocation_result
                             .total_runtime().total_seconds() / 3600.0)
        hourly_difference = int(diff_amount.total_seconds() / 3600.0)
        zero_time = allocation_result.time_to_zero()

        allocation_dict = {
            "threshold": hourly_credit,
            "current": hourly_runtime,
            "delta": ceil(delta.total_seconds() / 60),
            "burn": hourly_difference,
            "ttz": zero_time,
        }
        return allocation_dict

    def get_quota_dict(self):
        """
        NOTE: Remove when airport has been disabled.
        """
        quota = self.identity.quota
        quota_dict = {
            "mem": quota.memory,
            "cpu": quota.cpu,
            "storage": quota.storage,
            "storage_count": quota.storage_count,
        }
        return quota_dict

    def save(self, *args, **kwargs):
        """
        Whenever an IdentityMembership changes, update the provider
        specific quota too.
        """
        super(IdentityMembership, self).save(*args, **kwargs)
        try:
            from service.tasks.admin import set_provider_quota
            set_provider_quota.apply_async(args=[str(self.identity.uuid)])
        except Exception as ex:
            logger.warn("Unable to update service.quota.set_provider_quota.")
            raise

    def is_member(self, user):
        """
        Return whether the given user a member of the identity
        """
        return self.member in user.group_set.all()

    def __unicode__(self):
        return "%s can use identity %s" % (self.member, self.identity)

    class Meta:
        db_table = 'identity_membership'
        app_label = 'core'
        unique_together = ('identity', 'member')


class InstanceMembership(models.Model):

    """
    InstanceMembership allows group to see Instances in the frontend/API calls.
    InstanceMembership is the equivilant of
    'sharing' your instance with another Group/User
    Because InstanceMembers will not have that instance's Identity,
    calls to terminate/request imaging/attach/detach *should* fail.
    (This can also be dictated by permission)
    """
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    instance = models.ForeignKey('Instance')
    owner = models.ForeignKey(Group)

    def __unicode__(self):
        return "%s is a member-of %s" % (self.owner, self.instance)

    class Meta:
        db_table = 'instance_membership'
        app_label = 'core'
        unique_together = ('instance', 'owner')


