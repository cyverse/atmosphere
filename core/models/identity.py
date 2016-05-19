"""
  Core Identity models for atmosphere.
Note:
  Multiple users can 'own' an identity (IdentityMembership - group.py)
"""

from datetime import timedelta

from django.db import models

from threepio import logger
from uuid import uuid5, uuid4
from core.query import only_active_memberships

class Identity(models.Model):

    """
    An Identity is the minimal set of credentials necessary
    to authenticate against a single provider
    """

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    created_by = models.ForeignKey("AtmosphereUser")
    provider = models.ForeignKey("Provider")

    @classmethod
    def delete_identity(cls, username, provider_location):
        # Do not move up. ImportError.
        from core.models import AtmosphereUser, Group, Credential, Quota,\
            Provider, AccountProvider,\
            IdentityMembership

        provider = Provider.objects.get(location__iexact=provider_location)
        user = AtmosphereUser.objects.get(username=username)
        group = Group.objects.get(name=username)
        my_ids = Identity.objects.filter(
            created_by=user, provider=provider)
        for ident in my_ids:
            membership_set = ident.identity_memberships.all()
            membership_set.delete()
            ident.delete()
        group.delete()
        user.delete()
        return

    def can_share(self, django_user):
        """
        You CAN share an identity IFF:
        0. You are a staff user
        1. You are the original owner of the identity
        2. You are the leader of a group who contains the owner of the identity
        """
        # This person leads a group, may be able to share.
        # Check 0
        if django_user.is_staff:
            return True
        # Check 1
        original_owner = self.created_by
        if original_owner == django_user:
            return True
        # Check 2
        shared = False
        leader_groups = django_user.group_set.get(leaders__in=[django_user])
        for group in leader_groups:
            id_member = g.identity_memberships.get(identity=self)
            if not id_member:
                continue
            # ASSERT: You have SHARED access to the identity
            shared = True
            if original_owner in group.user_set.all():
                return True
        # User can't share.. Log the attempt for record-keeping
        if shared:
            logger.info("FAILED SHARE ATTEMPT: User:%s Identity:%s "
                        "Reason: You are not a leader of any group that "
                        "contains the actual owner of the identity (%s)."
                        % (django_user, self, original_owner))
        else:
            logger.info("FAILED SHARE ATTEMPT: User:%s Identity:%s "
                        % (django_user, self))

        return False

    def share(self, core_group, quota=None):
        """
        """
        from core.models import IdentityMembership, Quota, Allocation
        existing_membership = IdentityMembership.objects.filter(
            member=core_group, identity=self)
        if existing_membership:
            return existing_membership[0]

        # Ready to create new membership for this group
        if not quota:
            quota = Quota.default_quota()
        allocation = Allocation.default_allocation()
        new_membership = IdentityMembership.objects.get_or_create(
            member=core_group,
            identity=self,
            quota=quota,
            allocation=allocation)[0]
        return new_membership

    def unshare(self, core_group):
        """
        Potential problem:
        1. User X creates/imports an openstack account (& is the owner),
        2. User X shares identitymembership with User Y,
        3. User X or Y tries to unshare IdentityMembership with the opposing
        user.

        Solution:
        ONLY unshare if this user is the original owner of the identity
        """
        from core.models import IdentityMembership
        existing_membership = IdentityMembership.objects.filter(
            member=core_group, identity=self)
        return existing_membership[0].delete()

    def get_membership(self):
        identity_members = self.identity_memberships.all()
        group_names = [id_member.member for id_member in identity_members]
        # TODO: Add 'rules' if we want to hide specific users (staff, etc.)
        return group_names

    @classmethod
    def create_identity(cls, username, provider_location,
                        quota=None,
                        max_quota=False, account_admin=False, **kwarg_creds):
        """
        Create new User/Group & Identity for given provider_location
        NOTES:
        * kwargs prefixed with 'cred_' will be collected as credentials
        * Can assign optional flags:
          + max_quota - Assign the highest quota available, rather than
            default.
          + account_admin - Private Clouds only - This user should have ALL
            permissions including:
              * Image creation (Glance)
              * Account creation (Keystone)
              * Access to ALL instances launched over ALL users

          Atmosphere will run fine without an account_admin, but the above
          features will be disabled.
        """
        # Do not move up. ImportError.
        from core.models import Group, Quota,\
            Provider, AccountProvider, Allocation,\
            IdentityMembership

        provider = Provider.objects.get(location__iexact=provider_location)

        credentials = {}
        for (c_key, c_value) in kwarg_creds.items():
            if 'cred_' not in c_key.lower():
                continue
            c_key = c_key.replace('cred_', '')
            credentials[c_key] = c_value

        #DEV NOTE: 'New' identities are expected to have a router name directly assigned
        # upon creation. If the value is not passed in, we can ask the provider to select
        # the router with the least 'usage' to ensure an "eventually consistent" distribution
        # of users->routers.
        if 'router_name' not in credentials:
            credentials['router_name'] = provider.select_router()

        (user, group) = Group.create_usergroup(username)

        # NOTE: This specific query will need to be modified if we want
        # 2+ Identities on a single provider

        id_membership = IdentityMembership.objects.filter(
            member__name=user.username,
            identity__provider=provider,
            identity__created_by__username=user.username)
        if not id_membership:
            default_allocation = Allocation.default_allocation()
            # 1. Create an Identity Membership
            # DEV NOTE: I have a feeling that THIS line will mean
            #          creating a secondary identity for a user on a given
            #          provider will be difficult. We need to find a better
            #          workflow here..
            try:
                identity = Identity.objects.get(created_by=user,
                                                provider=provider)
            except Identity.DoesNotExist:
                new_uuid = uuid4()
                identity = Identity.objects.create(
                    created_by=user,
                    provider=provider,
                    uuid=str(new_uuid))
            id_membership = IdentityMembership.objects.get_or_create(
                identity=identity,
                member=group,
                allocation=default_allocation,
                quota=Quota.default_quota())
        # Either first in list OR object from two-tuple.. Its what we need.
        id_membership = id_membership[0]

        # ID_Membership exists.

        # 2. Make sure that all kwargs exist as credentials
        # NOTE: Because we assume only one identity per provider
        #       We can add new credentials to
        #       existing identities if missing..
        # In the future it will be hard to determine when we want to
        # update values on an identity Vs. create a second, new
        # identity.
        for (c_key, c_value) in credentials.items():
            Identity.update_credential(id_membership.identity, c_key, c_value)

        # 3. Assign a different quota, if requested
        if quota:
            id_membership.quota = quota
            id_membership.allocation = None
            id_membership.save()
        elif max_quota:
            quota = Quota.max_quota()
            id_membership.quota = quota
            id_membership.allocation = None
            id_membership.save()
        if account_admin:
            admin = AccountProvider.objects.get_or_create(
                provider=id_membership.identity.provider,
                identity=id_membership.identity)[0]

        # 5. Save the user to activate profile on first-time use
        user.save()
        # Return the identity
        return id_membership.identity

    @classmethod
    def update_credential(cls, identity, c_key, c_value, replace=False):
        from core.models import Credential
        test_key_exists = Credential.objects.filter(
            identity=identity,
            key=c_key)
        if len(test_key_exists) > 1:
            if not replace:
                raise ValueError("Found multiple entries for Credential: %s on Identity: %s" % (c_key, identity))
            test_key_exists.delete()
        elif test_key_exists:
            # Single selection
            test_key_exists = test_key_exists.get()
            logger.debug(
                "Conflicting Key Error: Key:%s Value:%s %s Value:%s" %
                (c_key, test_key_exists.value,
                 "(to replace with new value, set replace=True) New"
                 if not replace else "Replacement",
                 c_value))
            # No Dupes... But should we really throw an Exception here?
            if not replace:
                return test_key_exists
            test_key_exists.value = c_value
            test_key_exists.save()
            return test_key_exists
        return Credential.objects.get_or_create(
            identity=identity,
            key=c_key,
            value=c_value)[0]

    def provider_uuid(self):
        return self.provider.uuid

    def is_active(self, user=None):
        if user:
            return self.identity_memberships.filter(
                only_active_memberships(),
                member__user=user).count() > 0
        return self.provider.is_active()

    def creator_name(self):
        return self.created_by.username

    def project_name(self):
        project_name = self.get_credential('ex_project_name')
        if not project_name:
            project_name = self.get_credential('ex_tenant_name')
        if not project_name:
            project_name = self.get_credential('project_name')
        if not project_name:
            project_name = self.get_credential('tenant_name')
        return project_name


    def get_credential(self, key):
        cred = self.credential_set.filter(key=key)
        return cred[0].value if cred else None

    def get_credentials(self):
        cred_dict = {}
        for cred in self.credential_set.all():
            cred_dict[cred.key] = cred.value
        return cred_dict

    def get_all_credentials(self):
        cred_dict = {}
        for cred in self.provider.providercredential_set.all():
            cred_dict[cred.key] = cred.value
        # Allow overriding in the identity
        for cred in self.credential_set.all():
            cred_dict[cred.key] = cred.value
        return cred_dict

    def get_urls(self):
        return []

    def get_allocation(self):
        id_member = self.identity_memberships.all()[0]
        return id_member.allocation

    def get_total_hours(self):
        from service.monitoring import _get_allocation_result
        limit_instances = self.instance_set.all().values_list(
                'provider_alias', flat=True
            ).distinct()
        result = _get_allocation_result(
            self,
            limit_instances=limit_instances)
        total_hours = result.total_runtime().total_seconds()/3600.0
        hours = round(total_hours, 2)
        return hours

    def get_quota(self):
        id_member = self.identity_memberships.all()[0]
        return id_member.quota

    def get_allocation_usage(self):
        # Undoubtedly will cause circular dependencies
        from service.monitoring import _get_allocation_result
        allocation_result = _get_allocation_result(self)
        over_allocation, diff_amount = allocation_result.total_difference()
        burn_time = allocation_result.get_burn_rate()
        # Moving from seconds to hours
        hourly_credit = int(allocation_result
                            .total_credit().total_seconds() / 3600.0)
        hourly_runtime = int(allocation_result
                             .total_runtime().total_seconds() / 3600.0)
        hourly_difference = int(diff_amount.total_seconds() / 3600.0)
        zero_time = allocation_result.time_to_zero()
        return {
            "threshold": hourly_credit,  # Total amount
            "current": hourly_runtime,  # Total used
            "remaining": hourly_difference,
            "ttz": zero_time,  # Time Til Zero
        }



    def get_allocation_dict(self):
        id_member = self.identity_memberships.all()[0]
        allocation_dict = id_member.get_allocation_dict()
        return allocation_dict

    def get_quota_dict(self):
        id_member = self.identity_memberships.all()[0]
        # See core/models/membership.py#IdentityMembership
        quota_dict = id_member.get_quota_dict()
        allocation_dict = self.get_allocation_dict()
        if allocation_dict:
            quota_dict.update({"allocation": allocation_dict})
        return quota_dict

    def json(self):
        return {
            'id': self.id,
            'creator': self.created_by.username,
            'provider': self.provider.json(),
            'credentials': [cred.json() for cred
                            in self.credential_set.order_by('key')],
        }

    def __unicode__(self):
        output = "%s %s" % (self.provider, self.project_name())
        return output

    class Meta:
        db_table = "identity"
        app_label = "core"
        verbose_name_plural = "identities"
