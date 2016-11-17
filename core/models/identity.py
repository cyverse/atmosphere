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
from core.models.quota import Quota

class Identity(models.Model):

    """
    An Identity is the minimal set of credentials necessary
    to authenticate against a single provider
    """

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    created_by = models.ForeignKey("AtmosphereUser")
    provider = models.ForeignKey("Provider")
    quota = models.ForeignKey(Quota)

    @classmethod
    def find_instance(cls, instance_id):
        """
        Given an instance, find the identity that created it.
        """
        return Identity.objects.filter(instance__provider_alias=instance_id).first()

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

    def export_to_file(self, filename=None):
        """
        Depending on the ProviderType, appropriately
        generate 'export data' into an appropriate source-file
        """
        provider_type = self.provider.type.name
        if provider_type.lower() == 'openstack':
            from service.accounts.openstack_manager import AccountDriver
            return AccountDriver.generate_openrc(self, filename)
        return None

    def export(self):
        """
        Depending on the ProviderType, appropriately
        generate 'export data', a dict.
        """
        provider_type = self.provider.type.name
        if provider_type.lower() == 'openstack':
            from service.accounts.openstack_manager import AccountDriver
            return AccountDriver.export_identity(self)
        return None

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

    def share(self, core_group, allocation=None):
        """
        """
        from core.models import IdentityMembership, Quota, Allocation
        existing_membership = IdentityMembership.objects.filter(
            member=core_group, identity=self)
        if existing_membership:
            return existing_membership[0]

        # Ready to create new membership for this group
        if not allocation:
            allocation = Allocation.default_allocation()

        new_membership = IdentityMembership.objects.get_or_create(
            member=core_group,
            identity=self,
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
    def _kwargs_to_credentials(cls, kwarg_creds):
        """
        Takes a dictionary of `cred_*` key/values
        and returns back `*` key/value dictionary.
        Ignores any 'other' kwargs that may be present.
        """
        credentials = {}
        for (c_key, c_value) in kwarg_creds.items():
            if 'cred_' not in c_key.lower():
                continue
            c_key = c_key.replace('cred_', '')
            credentials[c_key] = c_value
        return credentials

    @classmethod
    def create_identity(cls, username, provider_location,
                        quota=None, allocation=None,
                        max_quota=False, account_admin=False, **kwarg_creds):
        """
        DEPRECATED: POST to v2/identities API to create an identity.
        """
        # Do not move up. ImportError.
        from core.models import Group, Quota,\
            Provider, AccountProvider, Allocation,\
            IdentityMembership

        provider = Provider.objects.get(location__iexact=provider_location)
        credentials = cls._kwargs_to_credentials(kwarg_creds)

        #DEV NOTE: 'New' identities are expected to have a router name directly assigned
        # upon creation. If the value is not passed in, we can ask the provider to select
        # the router with the least 'usage' to ensure an "eventually consistent" distribution
        # of users->routers.
        if 'router_name' not in credentials:
            credentials['router_name'] = provider.select_router()

        (user, group) = Group.create_usergroup(username)

        identity = cls._get_identity(user, group, provider, quota, credentials)
        # NOTE: This specific query will need to be modified if we want
        # 2+ Identities on a single provider

        id_membership = identity.share(group, allocation=allocation)
        # ID_Membership exists.

        # 3. Assign admin account, if requested
        if account_admin:
            AccountProvider.objects.get_or_create(
                provider=id_membership.identity.provider,
                identity=id_membership.identity)[0]

        # 4. Save the user to activate profile on first-time use
        # FIXME: only call .save() if 'no profile' test is True.
        # TODO: write a 'no profile' test f()
        user.save()

        # Return the identity
        return identity

    @classmethod
    def _get_identity(cls, user, group, provider, quota, credentials):
        try:
            # 1. Make sure that an Identity exists for the user/group+provider
            #FIXME: To make this *more* iron-clad, we should probably
            # create a method that looks at the provider, and selects
            # the username/project_name `key/value` pair, and looks *explicitly* for that pairing in an identity they have created..
            # Otherwise we are limiting the accounts a user can have to one/provider.
            identity = Identity.objects.get(
                    created_by=user, provider=provider)
            # 2. Make sure that all kwargs exist as credentials
            # NOTE: Because we assume only one identity per provider
            #       We can add new credentials to
            #       existing identities if missing..
            # In the future, we will only update the credentials *once*
            # during self._create_identity().
            for (c_key, c_value) in credentials.items():
                Identity.update_credential(identity, c_key, c_value)
        except Identity.DoesNotExist:
            # FIXME: we shouldn't have to create the uuid.. default does this.
            identity = cls._create_identity(user, group, provider, quota, credentials)
        return identity

    @classmethod
    def _create_identity(cls, user, group, provider, quota, credentials):
        new_uuid = uuid4()
        if not quota:
            quota = Quota.default_quota()
        identity = Identity.objects.create(
            created_by=user,
            provider=provider,
            quota=quota,
            uuid=str(new_uuid))
        for (c_key, c_value) in credentials.items():
            Identity.update_credential(identity, c_key, c_value)
        return identity

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
        # Hotfix to avoid errors in rtwo+OpenStack
        if 'ex_tenant_name' not in cred_dict:
            cred_dict['ex_tenant_name'] = self.project_name()
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
        return self.quota

    def total_usage(self, start_date, end_date):
        # Undoubtedly will cause circular dependencies
        from service.monitoring import _get_allocation_result
        allocation_result = _get_allocation_result(self, start_date, end_date)
        if not allocation_result:
            # Flag to the plugin you have an error in counting.
            return -1
        total_au = allocation_result.total_runtime().total_seconds() / 3600.0
        return total_au

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
