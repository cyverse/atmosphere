import uuid

from django.conf import settings
from django.utils import timezone
from threepio import logger

from core.models import (Identity, Quota)


# Call this to fire the 'quota_assigned' event
def set_quota_assigned(core_identity, quota, resource_request_id, approved_by, updated_at=None):
    from core.models import EventTable

    if not core_identity:
        raise Exception("Missing identity")
    if not quota:
        raise Exception("Missing quota")
    if not resource_request_id:
        raise Exception("Missing resource request ID")
    if not approved_by:
        raise Exception("Missing resource request approval user")
    if not updated_at:
        updated_at = timezone.now()
    timestamp = _to_timestamp(updated_at)
    entity_id = core_identity.created_by.username
    q_payload = quota.to_payload()
    event_payload = {
        "quota": q_payload,
        "resource_request": resource_request_id,
        "resource_request_approved_by": approved_by,
        "timestamp": timestamp
    }
    event = EventTable.create_event(
        name="quota_assigned",
        entity_id=entity_id,
        payload=event_payload)
    return event

def _to_timestamp(datetime):
    return datetime.isoformat().split('+')[0]+"Z"


# EVENT FIRED WHEN QUOTA IS ASSIGNED TO AN IDENTITY

def listen_for_quota_assigned(sender, instance, created, **kwargs):
    """
           This listener expects:
           EventType - 'quota_assigned'
           entity_id - "username" # Owner of the CoreIdentity that quota will be assigned to.

           # Event Payload Expected

           EventPayload - {
               "timestamp": "2017-01-01T12:00:00Z",
               "resource_request_id": 123,
               "resource_request_approved_by": "username",
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
           }

           The method should assign quota to the Identity.
        """
    event = instance
    from core.models import EventTable
    from service.quota import set_provider_quota
    if event.name != 'quota_assigned':
        return None
    logger.info('quota_assigned: %s' % event.__dict__)
    identity_uuid = event.entity_id
    identity = Identity.objects.get(uuid=identity_uuid)
    payload = event.payload
    quota_values = payload['quota']

    quota, created = Quota.objects.get_or_create(
        **quota_values
    )
    logger.info('Quota retrieved: %s, created: %s', quota, created)
    set_provider_quota(identity, quota=quota)
    logger.info("Cloud set identity to match quota: %s", identity)
    identity = Identity.objects.get(uuid=identity_uuid)
    identity.quota = quota
    identity.save()
    logger.info("DB set identity to match quota: %s", identity)
