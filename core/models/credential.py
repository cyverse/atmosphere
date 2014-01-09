"""
  Credential model for atmosphere.
Note:
  A Credential is 'one of many' that make up an Identity.
  (Identity - identity.py)
"""

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
