"""
  Credential model for atmosphere.
Note:
  A Credential is 'one of many' that make up an Identity.(Identity - identity.py)
"""

from django.db import models
from core.models.identity import Identity

class Credential(models.Model):
    """
    A Credential is a single piece of information necessary to authenticate a user
    Credentials are stored in a key/value map
    The user who entered the credential is recorded in order to allow for removal of private/sensitive information
    """
    key = models.CharField(max_length=256) # "Access Key", "Secret Key", "API Key"
    value = models.CharField(max_length=256) # 2ae8p0au, aw908e75iti, 120984723qwe
    identity =models.ForeignKey(Identity)

    def json(self):
        return {
                'key':self.key,
                'value':self.value,
                }

    def __unicode__(self):
        return "%s:%s" % (self.key,self.value)
    class Meta:
        db_table = 'credential'
        app_label = 'core'
