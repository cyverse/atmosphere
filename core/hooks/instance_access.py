from threepio import logger

from core.models import Instance


# EVENT FIRED TO ADD/REMOVE USERNAME FROM INSTANCE
def listen_for_add_share_instance_access(sender, instance, created, **kwargs):
    """
           This listener expects:
           EventType - 'add_share_instance_access'
           entity_id - "instance_id" # Provider_alias of the CoreInstance (Usernames will be shared with this instance)
           # Event Payload Expected

           EventPayload - {
               "timestamp": "2017-01-01T12:00:00Z",
               "username": "<atmosphere_user__username>",
                ...
           }

           The result of this method will:
           - Prepare a celery task that will:
             - Create a "Special playbook" that will deploy 'add_instance_access' playbook, passing in the <username> as an argument
        """
    from service.instance_access import _share_instance_access
    from service.driver import get_esh_driver
    event = instance
    if event.name != 'add_share_instance_access':
        return
    logger.info('add_share_instance_access: %s' % event.__dict__)

    payload = event.payload

    username = payload['username']
    instance_alias = payload['instance_id']
    instance = Instance.objects.get(provider_alias=instance_alias)
    logger.info("Instance retrieved: %s", instance)
    _share_instance_access(instance, username)
    return


def listen_for_remove_share_instance_access(sender, instance, created, **kwargs):
    """
           This listener expects:
           EventType - 'remove_share_instance_access'
           entity_id - "instance_id" # Provider_alias of the CoreInstance (Usernames will be shared with this instance)
           # Event Payload Expected

           EventPayload - {
               "timestamp": "2017-01-01T12:00:00Z",
               "username": "<atmosphere_user__username>",
                ...
           }

           The result of this method will:
           - Prepare a celery task that will:
             - Create a "Special playbook" that will deploy 'remove_instance_access' playbook, passing in the <username> as an argument
        """
    from service.instance_access import _remove_instance_access
    from service.driver import get_esh_driver
    event = instance
    if event.name != 'remove_share_instance_access':
        return
    logger.info('remove_share_instance_access: %s' % event.__dict__)

    payload = event.payload

    username = payload['username']
    instance_alias = payload['instance_id']
    instance = Instance.objects.get(provider_alias=instance_alias)
    _remove_instance_access(instance, username)
    return
