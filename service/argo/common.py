"""
Common component for Argo
"""

import os
import yaml
from django.conf import settings

from service.argo.rest_api import ArgoAPIClient
from service.argo.exception import (
    BaseWorkflowDirNotExist, ProviderWorkflowDirNotExist, WorkflowFileNotExist,
    WorkflowFileNotYAML, ArgoConfigFileNotExist, ArgoConfigFileNotYAML,
    ArgoConfigFileError
)


class ArgoContext:
    """
    Context that the Argo Workflow should be executing in
    """

    def __init__(
        self,
        api_host=None,
        api_port=None,
        token=None,
        namespace=None,
        ssl_verify=None,
        config=None
    ):
        """
        Create a context to execute ArgoWorkflow

        Args:
            api_host (str, optional): hostname of the Argo API Server. Defaults to None.
            api_port (int, optional): port of the Argo API Server. Defaults to None.
            token (str, optional): k8s bearer token. Defaults to None.
            namespace (str, optional): k8s namespace for the workflow. Defaults to None.
            ssl_verify (bool, optional): whether to verify ssl cert or not. Defaults to None.
            config (dict, optional): configuration, serve as a fallback if a
                config entry is not passed as a parameter. Defaults to None.
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

        if ssl_verify:
            self._ssl_verify = ssl_verify
        else:
            self._ssl_verify = config["ssl_verify"]

    def client(self):
        """
        Returns an ArgoAPIClient

        Returns:
            ArgoAPIClient: an API client with the config from this context
        """
        return ArgoAPIClient(
            self._api_host,
            self._api_port,
            self._token,
            self._namespace,
            verify=self._ssl_verify
        )


def _find_provider_dir(
    base_directory, provider_uuid, default_provider="default"
):
    """
    Check if the provider workflow directory exists

    Args:
        base_directory (str): base directory for workflow files
        provider_uuid (str): provider uuid
        default_provider (str, optional): default provider name. unset if None
            or "". Defaults to "default".

    Raises:
        ProviderWorkflowDirNotExist: provider workflow directory not exist
        BaseWorkflowDirNotExist: base workflow directory not exist

    Returns:
        str: path to provider workflow directory
    """
    try:
        # find provider directory
        provider_dirs = [
            entry
            for entry in os.listdir(base_directory) if entry == provider_uuid
        ]
        # try default provider if given provider dir does not exist
        if not provider_dirs and default_provider:
            provider_dirs = [
                entry for entry in os.listdir(base_directory)
                if entry == default_provider
            ]
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
        WorkflowFileNotExist: workflow definition file not exist
        ProviderWorkflowDirNotExist: provider workflow directory not exist

    Returns:
        str: path to the workflow file
    """
    try:
        # find workflow file
        wf_files = [
            entry
            for entry in os.listdir(provider_dir_path) if entry == filename
        ]
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
    wf_file_path = _find_workflow_file(
        provider_dir_path, filename, provider_uuid
    )

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
    wf_file_path = _find_workflow_file(
        provider_dir_path, filename, provider_uuid
    )

    try:
        # read workflow definition
        with open(wf_file_path, "r") as wf_file:
            wf_def = yaml.safe_load(wf_file.read())
    except yaml.YAMLError:
        raise WorkflowFileNotYAML(wf_file_path)
    except IOError:
        raise WorkflowFileNotExist(wf_file_path)

    return wf_def


def read_argo_config(config_file_path=None, provider_uuid=None):
    """
    Read configuration for Argo.
    Read from given path if specified, else read from path specified in the settings.
    Only config specific to the provider is returned, if provider uuid is not
    given, then uses the default one from the config.
    If there is no provider specific config, uses the default one.

    Args:
        config_file_path (str, optional): path to the config file. will use
            the default one from the setting if None. Defaults to None.
        provider_uuid (str, optional): uuid of the provider. Defaults to None.

    Raises:
        ArgoConfigFileNotExist: config file missing
        ArgoConfigFileNotYAML: config file not yaml
    """

    try:
        if not config_file_path:
            # path from settings
            config_file_path = settings.ARGO_CONFIG_FILE_PATH

        # read config file
        with open(settings.ARGO_CONFIG_FILE_PATH, "r") as config_file:
            all_config = yaml.safe_load(config_file.read())

        # validate config
        if not isinstance(all_config, dict):
            raise ArgoConfigFileError("config root not key-value")
        if "default" not in all_config:
            raise ArgoConfigFileError("default missing")
        if all_config["default"] not in all_config:
            raise ArgoConfigFileError("config for default provider missing")

        # uses the default provider, when no provider is specified
        if not provider_uuid:
            default_provider_uuid = all_config["default"]
            return all_config[default_provider_uuid]

        # if no provider specific config, uses the default one
        if provider_uuid not in all_config:
            default_provider_uuid = all_config["default"]
            return all_config[default_provider_uuid]

        return all_config[provider_uuid]
    except IOError:
        raise ArgoConfigFileNotExist(config_file_path)
    except yaml.YAMLError:
        raise ArgoConfigFileNotYAML(config_file_path)


def argo_context_from_config(config_file_path=None):
    """
    Construct an ArgoContext from a config file

    Args:
        config_file_path (str, optional): path to config file. Defaults to None.

    Returns:
        ArgoContext: argo context
    """
    # read configuration from file
    config = read_argo_config(config_file_path=config_file_path)

    # construct workflow context
    context = ArgoContext(config=config)
    return context
