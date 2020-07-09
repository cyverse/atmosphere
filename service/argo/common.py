"""
Common component for Argo
"""

import os
import json
import yaml
import time
from service.argo.rest_api import ArgoAPIClient
from service.argo.exception import *
from django.conf import settings

from threepio import celery_logger as logger

class ArgoContext:
    """
    Context that the Argo Workflow should be executing in
    """

    def __init__(self, api_host=None, api_port=None, token=None, namespace=None, config=None):
        """
        Create a context to execute ArgoWorkflow

        Args:
            api_host (str, optional): hostname of the Argo API Server. Defaults to None.
            api_port (int, optional): port of the Argo API Server. Defaults to None.
            token (str, optional): k8s bearer token. Defaults to None.
            namespace (str, optional): k8s namespace for the workflow. Defaults to None.
            config (dict, optional): configuration, serve as a fallback if a config entry is not passed as a parameter. Defaults to None.
        """
        if api_host:
            self._api_host = api_host
        else:
            self._api_host = config["api_host"]

        if api_port:
            self._api_port = api_port
        else:
            self._api_port = config["api_port"]

        if token:
            self._token = token
        else:
            self._token = config["token"]

        if namespace:
            self._namespace = namespace
        else:
            self._namespace = config["namespace"]

    def client(self):
        """
        Returns an ArgoAPIClient

        Returns:
            ArgoAPIClient: an API client with the config from this context
        """
        return ArgoAPIClient(self._api_host, self._api_port, self._token, self._namespace,
                            # Argo server currently has self-signed cert
                             verify=False)

def _find_provider_dir(base_directory, provider_uuid, default_provider="default"):
    """
    Check if the provider workflow directory exists

    Args:
        base_directory (str): base directory for workflow files
        provider_uuid (str): provider uuid
        default_provider (str, optional): default provider name. unset if None or "". Defaults to "default".

    Raises:
        ProviderWorkflowDirNotExist: [description]
        BaseWorkflowDirNotExist: [description]

    Returns:
        [type]: [description]
    """
    try:
        # find provider directory
        provider_dirs = [entry for entry in os.listdir(base_directory)
                            if entry == provider_uuid]
        # try default provider if given provider dir does not exist
        if not provider_dirs and default_provider:
            provider_dirs = [entry for entry in os.listdir(base_directory)
                             if entry == default_provider]
        if not provider_dirs:
            raise ProviderWorkflowDirNotExist(provider_uuid)

        provider_dir = base_directory + "/" + provider_dirs[0]
        return provider_dir
    except OSError:
        raise BaseWorkflowDirNotExist(base_directory)

def _find_workflow_file(provider_dir_path, filename, provider_uuid):
    """
    Find the path of the workflow file, and check if the file exists

    Args:
        provider_dir_path (str): path to the provider workflow directory
        filename (str): workflow definition filename
        provider_uuid (str): provider uuid

    Raises:
        WorkflowFileNotExist: [description]
        ProviderWorkflowDirNotExist: [description]

    Returns:
        str: path to the workflow file
    """
    try:
        # find workflow file
        wf_files = [entry for entry in os.listdir(provider_dir_path)
                    if entry == filename]
        if not wf_files:
            raise WorkflowFileNotExist(provider_uuid, filename)

        # construct path
        wf_file_path = provider_dir_path + "/" + wf_files[0]
        return wf_file_path
    except OSError:
        raise ProviderWorkflowDirNotExist(provider_uuid)

def argo_lookup_workflow(base_directory, filename, provider_uuid):
    """
    Lookup workflow by name and cloud provider

    Args:
        base_directory (str): base directory for workflow files
        filename (str): workflow filename
        provider_uuid (str): the provider uuid

    Raises:
        WorkflowFileNotYAML: unable to parse workflow definition file as YAML
        WorkflowFileNotExist: unable to open/read workflow definition file

    Returns:
        ArgoWorkflow: JSON object representing the workflow if found, None otherwise
    """
    provider_dir_path = _find_provider_dir(base_directory, provider_uuid)
    wf_file_path = _find_workflow_file(provider_dir_path, filename, provider_uuid)

    try:
        # read workflow definition
        with open(wf_file_path, "r") as wf_file:
            wf_def = yaml.safe_load(wf_file.read())
    except yaml.YAMLError:
        raise WorkflowFileNotYAML(wf_file_path)
    except IOError:
        raise WorkflowFileNotExist(wf_file_path)

    return wf_def

def argo_lookup_yaml_file(base_directory, filename, provider_uuid):
    """
    Lookup yaml file by filename and cloud provider and read the yaml file

    Args:
        base_directory (str): base directory for workflow files
        filename (str): yaml filename
        provider_uuid (str): the provider uuid

    Raises:
        WorkflowFileNotYAML: unable to parse workflow definition file as YAML
        WorkflowFileNotExist: unable to open/read workflow definition file

    Returns:
        ArgoWorkflow: JSON object representing the workflow if found, None otherwise
    """
    provider_dir_path = _find_provider_dir(base_directory, provider_uuid)
    wf_file_path = _find_workflow_file(provider_dir_path, filename, provider_uuid)

    try:
        # read workflow definition
        with open(wf_file_path, "r") as wf_file:
            wf_def = yaml.safe_load(wf_file.read())
    except yaml.YAMLError:
        raise WorkflowFileNotYAML(wf_file_path)
    except IOError:
        raise WorkflowFileNotExist(wf_file_path)

    return wf_def



