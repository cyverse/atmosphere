"""
  Credential model for atmosphere.
Note:
  A Credential is 'one of many' that make up an Identity.
  (Identity - identity.py)
"""

from uuid import uuid4
from django.db import models
from core.models.identity import Identity
from core.models.provider import Provider


class ProviderCredential(models.Model):

    """
    A ProviderCredential is a single piece of information used by all
    identities on the provider.
    Credentials are stored in a key/value map
    """
    # Euca Examples: "EC2 Url", "S3 Url",
    # OStack Examples: "Auth URL", "Admin URL", "Admin Tenant",
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    #                  "Default Region", "Default Router"
    key = models.CharField(max_length=256)
    # 2ae8p0au, aw908e75iti, 120984723qwe
    value = models.CharField(max_length=256)
    provider = models.ForeignKey(Provider)

    def __unicode__(self):
        return "%s:%s" % (self.key, self.value)

    class Meta:
        db_table = 'provider_credential'
        app_label = 'core'


class Credential(models.Model):

    """
    A Credential is a single piece of information used to authenticate a user
    Credentials are stored in a key/value map
    The user who entered the credential is recorded
    in order to allow for removal of private/sensitive information
    """
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    # Examples: "Access Key", "Secret Key", "API Key"
    key = models.CharField(max_length=256)
    # 2ae8p0au, aw908e75iti, 120984723qwe
    value = models.CharField(max_length=256)
    identity = models.ForeignKey(Identity)

    def json(self):
        return {
            'key': self.key,
            'value': self.value,
        }

    def __unicode__(self):
        return "%s:%s" % (self.key, self.value)

    class Meta:
        db_table = 'credential'
        app_label = 'core'


def get_groups_using_credential(cred_key, cred_value, provider):
    from threepio import logger
    credentials_found = Credential.objects.filter(
        key=cred_key,
        value=cred_value,
        identity__provider=provider)
    if not credentials_found:
        print "No credentials found in the DB for provider %s with %s=%s"\
              % (provider, cred_key, cred_value)
        logger.debug(
            "No credentials found in the DB for provider %s with %s=%s" %
            (provider, cred_key, cred_value))
        return []
    all_affected_members = []
    for cred in credentials_found:
        affected_identity = cred.identity
        affected_membership = affected_identity.identity_memberships.all()
        all_affected_members.extend(affected_membership)
    return all_affected_members
