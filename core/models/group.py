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
        only_current, only_active_memberships, only_current_provider
    )


class Group(DjangoGroup):

    """
    Extend the Django Group model to support 'membership'
    """
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
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

    def __unicode__(self):
        return "AtmosphereGroup %s" % (self.name,)

    def is_leader(self, test_user):
        return any(user for user in self.leaders if user == test_user)

    @property
    def is_private(self):
        """
        For now, this is how we can verify if the group is 'private'.
        Later, we might have to remove the property and include a 'context user'
        so that we can determine the ownership (of the group, or that the name is a perfect match, etc.)
        """
        return self.memberships.filter(is_leader=True).count() == 1

    @property
    def leaders(self):
        return self.memberships.filter(is_leader=True)

    @property
    def users(self):
        return self.memberships.all()

    def get_users(self):
        user_ids = self.users.values_list('user__id', flat=True)
        return AtmosphereUser.objects.filter(id__in=user_ids)

    def get_leaders(self):
        user_ids = self.leaders.values_list('user__id', flat=True)
        return AtmosphereUser.objects.filter(id__in=user_ids)

    @property
    def identitymembership_set(self):
        logger.warn("WARNING - THIS FIELD DEPRECATED for `identity_memberships` REPLACE THE REFERENCE USING THIS LINE")
        return self.identity_memberships

    @property
    def current_identity_memberships(self):
        return self.identity_memberships.filter(only_active_memberships())

    @staticmethod
    def for_identity(identity_uuid):
        return Group.objects.filter(identity_memberships__identity__uuid=identity_uuid)

    @property
    def current_identities(self):
        return Identity.shared_with_group(self).filter(only_current_provider())

    @property
    def current_providers(self):
        return Provider.shared_with_group(self).filter(only_current(), active=True)

    @classmethod
    def check_membership(cls, test_user, membership_groups):
        """
        PARAMS:
          test_user - DjangoUser to be tested
          membership_groups - List of groups allowed membership to... Something.
        RETURNS:
          True/False - If any of the users groups grants membership access.
        """
        return any(membership.group for membership
                   in test_user.memberships.all() if membership.group in membership_groups)

    @classmethod
    def check_access(cls, user, groupname):
        group = Group.objects.filter(name=groupname).first()
        return GroupMembership.objects.filter(user=user, group=group).exists()

    @classmethod
    def create_usergroup(cls, username, group_name=None, is_leader=False):
        # TODO: ENFORCEMENT of lowercase-only usernames until cleared by mgmt.
        username = username.lower()
        if not group_name:
            group_name = username
        user = AtmosphereUser.objects.get_or_create(username=username)[0]
        group = Group.objects.get_or_create(name=group_name)[0]
        group.user_set.add(user)

        member = GroupMembership.objects.get_or_create(user=user, group=group)[0]
        if is_leader:
            member.is_leader = True
            member.save()
        return (user, group)

    def json(self):
        return {
            'id': self.id,
            'name': self.name
        }

    class Meta:
        db_table = 'group'
        app_label = 'core'


class GroupMembership(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey('AtmosphereUser', related_name='memberships')
    group = models.ForeignKey(Group, related_name='memberships')
    is_leader = models.BooleanField(default=False)

    def __unicode__(self):
        return "%s is a %s of %s"  % (
            self.user,
            "leader" if self.is_leader else "member",
            self.group)

    class Meta:
        db_table = 'group_members'
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
        return IdentityMembership.objects.filter(member=group)

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

    def is_member(self, user):
        """
        Return whether the group in this identity-membership
        allows access to _user_
        """
        group = self.member
        return user.id in group.memberships.values_list('user', flat=True)

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


