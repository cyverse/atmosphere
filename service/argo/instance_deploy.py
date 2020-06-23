"""
Deploy instance.
"""

import yaml
import json
from service.argo.wf_call import argo_workflow_exec
from service.argo.exception import WorkflowDataFileNotExist

from django.conf import settings

from threepio import celery_logger

def argo_deploy_instance(
    provider_name,
    server_ip,
    username,
    timezone,
):
    """
    run Argo workflow to deploy an instance

    Args:
        provider_name (str): provider name
        server_ip (str): ip of the server instance
        username (str): username
        timezone (str): timezone of the provider, e.g. America/Arizona

    Raises:
        exc: exception thrown
    """
    try:
        wf_data = _get_workflow_data(server_ip, username, timezone)

        # TODO
        # put config file path in config
        config_file_path = "/opt/dev/atmosphere-docker-secrets/argo_config.yml"

        status = argo_workflow_exec("instance_deploy.yml", provider_name, wf_data, config_file_path=config_file_path, wait=True)
        celery_logger.debug("ARGO, workflow complete")
        celery_logger.debug(status)
    except Exception as exc:
        celery_logger.debug("ARGO, argo_deploy_instance(), {}, {}".format(type(exc), exc))
        raise exc

def _get_workflow_data(server_ip, username, timezone):
    """
    Generate the data structure to be passed to the workflow

    Args:
        server_ip (str): ip of the server instance
        username (str): username of the owner of the instance
        timezone (str): timezone of the provider

    Raises:
        WorkflowDataFileNotExist: private key file not exist

    Returns:
        dict: {"arguments": {"parameters": [{"name": "", "value": ""}]}}
    """
    wf_data = {"arguments": {"parameters": []}}
    wf_data["arguments"]["parameters"].append({"name": "server-ip", "value": server_ip})
    wf_data["arguments"]["parameters"].append({"name": "user", "value": username})
    wf_data["arguments"]["parameters"].append({"name": "tz", "value": timezone})
    wf_data["arguments"]["parameters"].append({"name": "zoneinfo", "value": "/usr/share/zoneinfo/US/Arizona"})
    try:
        private_key_file_path = settings.ATMOSPHERE_PRIVATE_KEYFILE
        private_key_file = open(private_key_file_path)
        private_key = private_key_file.read()
        private_key_file.close()
        wf_data["arguments"]["parameters"].append({"name": "private-ssh-key", "value": private_key})
    except IOError as exc:
        celery_logger.debug("ARGO, private_key_file not found")
        raise WorkflowDataFileNotExist(private_key_file_path)

    return wf_data