"""
  Core Identity models for atmosphere.
Note:
  Multiple users can 'own' an identity (IdentityMembership - group.py)
"""

from datetime import timedelta

from django.db import models
from django.contrib.auth.models import User

from threepio import logger

class Identity(models.Model):
    """
    An Identity is the minimal set of credentials necessary
    to authenticate against a single provider
    """

    created_by = models.ForeignKey(User)
    provider = models.ForeignKey("Provider")

    @classmethod
    def create_identity(cls, username, provider_location,
                        max_quota=False, account_admin=False, **kwarg_creds):
        """
        Create new User/Group & Identity for given provider_location
        NOTES:
        * kwargs prefixed with 'cred_' will be collected as credentials
        * Can assign optional flags:
          + max_quota - Assign the highest quota available, rather than default.
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

        print kwarg_creds
        credentials = {}
        for (c_key,c_value) in kwarg_creds.items():
            if 'cred_' not in c_key.lower():
                continue
            c_key = c_key.replace('cred_','')
            credentials[c_key] = c_value
        print credentials

        (user, group) = Group.create_usergroup(username)

        #NOTE: This specific query will need to be modified if we want
        # 2+ Identities on a single provider

        id_membership = IdentityMembership.objects.filter(
            member__name= user.username,
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
        # update values on an identity Vs. create a second, new identity.
        for (c_key,c_value) in credentials.items():
            test_key_exists = Credential.objects.filter(
                    identity=id_membership.identity,
                    key=c_key)
            if test_key_exists:
                logger.info("Conflicting Key Errror: Key:%s Value:%s "
                "Replacement:%s" % (c_key, c_value, test_key_exists[0].value))
                #No Dupes... But should we really throw an Exception here?
                continue
            Credential.objects.get_or_create(
                identity=id_membership.identity,
                key=c_key,
                value=c_value)[0]
        #4. Assign a different quota, if requested
        if max_quota:
            quota = Quota.get_max_quota()
            id_membership.quota = quota
            id_membership.save
        if account_admin:
            admin = AccountProvider.objects.get_or_create(
                        provider=id_membership.identity.provider,
                        identity=id_membership.identity)[0]

        #5. Save the user to activate profile on first-time use
        user.save()
        #Return the identity
        return id_membership.identity

    def creator_name(self):
        return self.created_by.username

    def get_credentials(self):
        cred_dict = {}
        for cred in self.credential_set.all():
            cred_dict[cred.key] = cred.value
        return cred_dict

    def get_quota(self):
        id_member = self.identitymembership_set.all()[0]
        return id_member.quota

    def get_quota_dict(self):
        #Don't move it up. Circular reference.
        from service.allocation import get_time, print_timedelta
        id_member = self.identitymembership_set.all()[0]
        quota = id_member.quota
        quota_dict = {
            "mem": quota.memory,
            "cpu": quota.cpu,
            "disk": quota.storage,
            "disk_count": quota.storage_count,
            "suspended_count": quota.suspended_count,
        }
        if id_member.allocation:
            allocation = id_member.allocation
            time_used = get_time(id_member.identity.created_by,
                                 id_member.identity.id,
                                 timedelta(minutes=allocation.delta))
            current_mins = int(time_used.total_seconds() / 60)
            quota_dict.update({
                "allocation": {
                    "threshold": allocation.threshold,
                    "current": current_mins,
                    "delta": allocation.delta,
                    "ttz": allocation.threshold - current_mins
                }
            })
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
