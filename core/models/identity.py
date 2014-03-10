"""
  Core Identity models for atmosphere.
Note:
  Multiple users can 'own' an identity (IdentityMembership - group.py)
"""

from datetime import timedelta

from django.db import models

from threepio import logger


class Identity(models.Model):
    """
    An Identity is the minimal set of credentials necessary
    to authenticate against a single provider
    """

    created_by = models.ForeignKey("AtmosphereUser")
    provider = models.ForeignKey("Provider")

    @classmethod
    def delete_identity(cls, username, provider_location):
        #Do not move up. ImportError.
        from core.models import AtmosphereUser, Group, Credential, Quota,\
            Provider, AccountProvider,\
            IdentityMembership, ProviderMembership

        provider = Provider.objects.get(location__iexact=provider_location)
        user = AtmosphereUser.objects.get(username=username)
        group = Group.objects.get(name=username)
        my_ids = Identity.objects.filter(
            created_by=user, provider=provider)
        for ident in my_ids:
            membership_set = ident.identitymembership_set.all()
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
        #This person leads a group, may be able to share.
        #Check 0
        if django_user.is_staff:
            return True
        #Check 1
        original_owner = self.created_by
        if original_owner == django_user:
            return True
        #Check 2
        shared = False
        leader_groups = django_user.group_set.get(leaders__in=[django_user])
        for group in leader_groups:
            id_member = g.identitymembership_set.get(identity=self)
            if not id_member:
                continue
            #ASSERT: You have SHARED access to the identity
            shared = True
            if original_owner in group.user_set.all():
                return True
        #User can't share.. Log the attempt for record-keeping
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
        from core.models import IdentityMembership, ProviderMembership
        existing_membership = IdentityMembership.objects.filter(
            member=core_group, identity=self)
        if existing_membership:
            return existing_membership[0]

        #User does not already have membership - Check for provider membership
        prov_membership = ProviderMembership.objects.filter(
            member=core_group, provider=self.provider)
        if not prov_membership:
            raise Exception("Cannot share identity membership before the"
                            " provider is shared")

        #Ready to create new membership for this group
        if not quota:
            quota = Quota.default_quota()
        allocation = Allocation.default_allocation()
        new_membership = IdentityMembership.objects.get_or_create(
            member=core_group, identity=self, quota=quota, allocation=allocation)[0]
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
        identity_members = self.identitymembership_set.all()
        group_names = [id_member.member for id_member in identity_members]
        #TODO: Add 'rules' if we want to hide specific users (staff, etc.)
        return group_names

    @classmethod
    def create_identity(cls, username, provider_location,
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
        #Do not move up. ImportError.
        from core.models import Group, Credential, Quota,\
            Provider, AccountProvider,\
            IdentityMembership, ProviderMembership

        provider = Provider.objects.get(location__iexact=provider_location)

        credentials = {}
        for (c_key, c_value) in kwarg_creds.items():
            if 'cred_' not in c_key.lower():
                continue
            c_key = c_key.replace('cred_', '')
            credentials[c_key] = c_value

        (user, group) = Group.create_usergroup(username)

        #NOTE: This specific query will need to be modified if we want
        # 2+ Identities on a single provider

        id_membership = IdentityMembership.objects.filter(
            member__name=user.username,
            identity__provider=provider,
            identity__created_by__username=user.username)
        if not id_membership:
            #1. Create a Provider Membership
            p_membership = ProviderMembership.objects.get_or_create(
                provider=provider, member=group)[0]

            #2. Create an Identity Membership
            identity = Identity.objects.get_or_create(
                created_by=user, provider=provider)[0]
            #Two-tuple, (Object, created)
            id_membership = IdentityMembership.objects.get_or_create(
                identity=identity, member=group, quota=Quota.default_quota())
        #Either first in list OR object from two-tuple.. Its what we need.
        id_membership = id_membership[0]

        #ID_Membership exists.

        #3. Make sure that all kwargs exist as credentials
        # NOTE: Because we assume only one identity per provider
        #       We can add new credentials to
        #       existing identities if missing..
        # In the future it will be hard to determine when we want to
        # update values on an identity Vs. create a second, new
        # identity.
        for (c_key, c_value) in credentials.items():
            test_key_exists = Credential.objects.filter(
                identity=id_membership.identity,
                key=c_key)
            if test_key_exists:
                logger.info("Conflicting Key Error: Key:%s Value:%s "
                            "Replacement:%s" %
                            (c_key, c_value, test_key_exists[0].value))
                #No Dupes... But should we really throw an Exception here?
                continue
            Credential.objects.get_or_create(
                identity=id_membership.identity,
                key=c_key,
                value=c_value)[0]
        #4. Assign a different quota, if requested
        if max_quota:
            quota = Quota.max_quota()
            id_membership.quota = quota
            id_membership.save()
        if account_admin:
            admin = AccountProvider.objects.get_or_create(
                provider=id_membership.identity.provider,
                identity=id_membership.identity)[0]

        #5. Save the user to activate profile on first-time use
        user.save()
        #Return the identity
        return id_membership.identity

    def is_active(self):
        return self.provider.is_active()

    def creator_name(self):
        return self.created_by.username

    def get_credential(self, key):
        cred = self.credential_set.filter(key=key)
        return cred[0].value if cred else None

    def get_credentials(self):
        cred_dict = {}
        for cred in self.credential_set.all():
            cred_dict[cred.key] = cred.value
        return cred_dict

    def get_allocation(self):
        id_member = self.identitymembership_set.all()[0]
        return id_member.allocation

    def get_quota(self):
        id_member = self.identitymembership_set.all()[0]
        return id_member.quota

    def get_allocation_dict(self):
        id_member = self.identitymembership_set.all()[0]
        allocation_dict = id_member.get_allocation_dict()
        return allocation_dict

    def get_quota_dict(self):
        id_member = self.identitymembership_set.all()[0]
        #See core/models/group.py#IdentityMembership
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
        output = "%s %s - " % (self.provider, self.created_by.username)
        output += "Credentials {"
        for c in self.credential_set.order_by('key'):
            output += "%s, " % (c.key,)
        output = output[:-2] + "}"
        return output

    class Meta:
        db_table = "identity"
        app_label = "core"
        verbose_name_plural = "identities"
