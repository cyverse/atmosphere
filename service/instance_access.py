from threepio import logger

from service.driver import get_esh_driver
from service.tasks.driver import _deploy_instance_playbook

from core.models import SSHKey
from core.events.serializers.instance_playbook_history import _create_instance_playbook_history_event

def _remove_instance_access(instance, username, delay=False):
    identity = instance.created_by_identity
    logger.info("Instance retrieved: %s", instance)
    driver = get_esh_driver(identity)
    user_ssh_keys = SSHKey.objects.filter(atmo_user__username=username)
    user_keys = [k.pub_key for k in user_ssh_keys]
    extra_vars = {
        "USERSSHKEYS": user_keys,
    }
    playbook_name = "remove_user.yml"
    playbook_arguments = {
        "ATMOUSERNAME": username,
    }
    args = (driver.__class__, driver.provider, driver.identity,
            instance.provider_alias, playbook_name, playbook_arguments, extra_vars)
    event_kwargs = {
        "instance": instance.provider_alias,
        "playbook": playbook_name,
        "arguments": playbook_arguments,
        "status": "queued",
        "message": ""
    }
    _create_instance_playbook_history_event(**event_kwargs)
    logger.info("Deploy ansible playbook to remove instance %s with username %s", instance, username)
    # Call method if delay is true
    if delay:
        return _deploy_instance_playbook(*args)
    subtask = _deploy_instance_playbook.si(*args)
    async_task = subtask.apply_async()
    return async_task


def _retry_instance_access(snapshot):
    instance = snapshot.instance
    identity = instance.created_by_identity
    driver = get_esh_driver(identity)
    extra_vars = {}
    args = (driver.__class__, driver.provider, driver.identity,
            instance.provider_alias, snapshot.playbook_name, snapshot.playbook_arguments, extra_vars)
    logger.info("Re-Deploy ansible playbook to share instance %s with playbook args %s", instance, snapshot.playbook_arguments)
    subtask = _deploy_instance_playbook.si(*args)
    async_task = subtask.apply_async()
    return async_task


def _share_instance_access(instance, username, delay=False):
    identity = instance.created_by_identity
    driver = get_esh_driver(identity)
    user_ssh_keys = SSHKey.objects.filter(atmo_user__username=username)
    user_keys = [k.pub_key for k in user_ssh_keys]
    extra_vars = {
        "USERSSHKEYS": user_keys,
        "ATMOUSERNAME": username,
    }
    playbook_name = "add_user.yml"
    args = (
        driver.__class__, driver.provider, driver.identity,
        instance.provider_alias, playbook_name, extra_vars)
    # Call method if delay is true
    logger.info("Deploy ansible playbook to share instance %s with username %s", instance, username)
    event_kwargs = {
        "instance": instance.provider_alias,
        "playbook": playbook_name,
        "arguments": extra_vars,
        "status": "queued",
        "message": ""
    }
    _create_instance_playbook_history_event(**event_kwargs)
    if delay:
        return _deploy_instance_playbook(*args)
    subtask = _deploy_instance_playbook.si(*args)
    async_task = subtask.apply_async()
    return async_task
