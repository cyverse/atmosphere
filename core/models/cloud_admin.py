"""
Cloud Administrator model for atmosphere
"""
from django.db import models
from core.models.user import AtmosphereUser
from core.models.provider import Provider
import uuid


class CloudAdministrator(models.Model):
    """
    This model is reserved exclusively for users who are in control of an
    entire 'cloud' provider.
    CloudAdministrators have access to:
    * Any 'AccountProvider' identities for that provider
      * Allows access to all 'visible' tenants w/o giving 'emulate/identity'
        access
    * Perform special actions:
      * Create/Approve/Deny/Check status of [Allocation/Quota/Machine]Requests
      * Create/Update VM State Policies (What counts for/against allocation)
      * Create/Update VM actions on over Allocation
        (Suspend/Shutoff/Email/etc.)
    This class only applies to Private clouds!
    """
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(AtmosphereUser)
    provider = models.ForeignKey(Provider)

    def __unicode__(self):
        return "Cloud Administrator: %s Provider:%s"\
            % (self.user, self.provider)

    class Meta:
        db_table = 'cloud_administrator'
        app_label = 'core'


def cloud_admin_list(user):
    return CloudAdministrator.objects.filter(user=user)


def admin_provider_list(user):
    cloud_admins = cloud_admin_list(user)
    provider_ids = cloud_admins.values_list('provider', flat=True)
    return Provider.objects.filter(id__in=provider_ids)


def get_cloud_admin_for_provider(user, provider_uuid):
    try:
        return cloud_admin_list(user)\
            .get(provider__uuid=provider_uuid)
    except CloudAdministrator.DoesNotExist:
        return None
