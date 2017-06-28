from django.conf import settings
from django.utils import timezone
from threepio import logger

from core.models import (Identity, Quota)


# EVENT FIRED TO ASSIGN QUOTA TO AN IDENTITY
def listen_for_quota_assigned(sender, instance, created, **kwargs):
    """
           This listener expects:
           EventType - 'quota_assigned'
           entity_id - "username" # Owner of the CoreIdentity that quota will be assigned to.

           # Event Payload Expected

           EventPayload - {
               "timestamp": "2017-01-01T12:00:00Z",
               "identity": "<core_identity_uuid>",
               "quota": {
                    "cpu": 16,
                    "memory": 128,
                    "storage": 10,
                    "instance_count": 10,
                    "snapshot_count": 10,
                    "storage_count": 10,
                    "floating_ip_count": 10,
                    "port_count": 10
                }
                ...
           }

           The result of this method will:
           - Set the quota for the cloud provider of the Identity
           - assign the quota to the Identity
        """
    event = instance
    from core.models import EventTable
    from service.quota import set_provider_quota
    if event.name != 'quota_assigned':
        return
    logger.info('quota_assigned: %s' % event.__dict__)

    username = event.entity_id
    payload = event.payload

    quota_values = payload['quota']
    identity_uuid = payload['identity']
    identity = Identity.objects.get(uuid=identity_uuid)

    created = False
    quota = Quota.objects.filter(
        **quota_values
    ).order_by('pk').first()
    if not quota:
        quota = Quota.objects.create(**quota_values)
        created = True
    logger.info('Quota retrieved: %s, created: %s', quota, created)
    set_provider_quota(str(identity.uuid), quota=quota)
    logger.info("Set the quota for cloud provider to match: %s", identity)
    identity = Identity.objects.get(uuid=identity_uuid)
    identity.quota = quota
    identity.save()
    logger.info("DB set identity to match quota: %s", identity)
    return
