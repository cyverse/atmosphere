"""
Listen for `instance_playbook_status_updated` events and update the snapshot table accordingly
"""
from core.models import InstancePlaybookSnapshot, Instance

from threepio import logger

def _rebuild_playbook_history():
    """
    For testing
    """
    from core.models import EventTable
    InstancePlaybookSnapshot.objects.all().delete()
    for event in EventTable.instance_history_playbooks.all():
        _update_instance_playbook_snapshot(event)


def listen_for_playbook_history_update(sender, instance, created, **kwargs):
    """
       This listener expects:
       EventType - 'instance_playbook_history_updated'

       The result of this method will:
       - Update the InstancePlaybookSnapshot object to represents the latest history seen by DB
    """
    event = instance
    if event.name != 'instance_playbook_history_updated':
        return
    logger.info('Found instance_playbook_history_updated event: %s', event.__dict__)
    _update_instance_playbook_snapshot(event)
    return


def _update_instance_playbook_snapshot(event):
    payload = event.payload
    instance_alias = event.entity_id
    playbook_name = payload['ansible_playbook']
    playbook_args = payload['arguments']
    status = payload['status']
    instance = Instance.objects.get(provider_alias=instance_alias)
    object_updated, created = InstancePlaybookSnapshot.objects.update_or_create(
        instance=instance,
        playbook_name=playbook_name,
        playbook_arguments=playbook_args,
        defaults={"status": status})
    logger.info('object_updated: %s, created: %s', object_updated, created)
    return object_updated
