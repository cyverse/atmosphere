"""
  Core Identity models for atmosphere.
Note:
  Multiple users can 'own' an identity (IdentityMembership - group.py)
"""

from datetime import timedelta

from django.db import models
from django.contrib.auth.models import User

class Identity(models.Model):
    """
    An Identity is the minimal set of credentials necessary
    to authenticate against a single provider
    """

    created_by = models.ForeignKey(User)
    provider = models.ForeignKey("Provider")

    def creator_name(self):
        return self.created_by.username

    def credential_list(self):
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
        }
        if id_member.allocation:
            allocation = id_member.allocation
            time_used = get_time(id_member.identity.created_by,
                                 id_member.identity.id,
                                 timedelta(minutes=allocation.delta))
            quota_dict.update({
                "allocation": {
                    "threshold": allocation.threshold,
                    "current": int(time_used.total_seconds() / 60),
                    "delta": allocation.delta
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
