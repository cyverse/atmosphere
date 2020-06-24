"""
Execute Argo Workflow
"""

import os
import json
import yaml
import time
from service.argo.rest_api import ArgoAPIClient
from service.argo.exception import *
from django.conf import settings

from threepio import celery_logger as logger

class ArgoWorkflowExeContext:
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

class ArgoWorkflow:
    """
    A generic interface for using Argo Worflow.
    """

    def __init__(self, wf_def):
        """Creates an ArgoWorkflow object from a workflow definition

        Args:
            wf_def (dict): workflow definition read/parsed from yaml
        """
        self._wf_def = wf_def

    def execute(self, context, wf_data={}):
        """
        Execute the workflow with given context and data, and wait for completion

        Args:
            context (ArgoWorkflowExeContext): context to execute the workflow in
            wf_data (dict, optional): data to be passed to workflow. Defaults to {}.

        Returns:
            (str, dict): workflow name and status of the workflow {"complete": bool, "success": bool, "error": bool}
        """
        def polling(wf_name, interval, repeat_count):
            for _ in range(repeat_count):
                status = ArgoWorkflow.status(context, wf_name)
                if status and "complete" in status and status["complete"]:
                    return status
                time.sleep(interval)
            return None

        json_resp = self.exec_no_wait(context, wf_data=wf_data)
        wf_name = json_resp["metadata"]["name"]

        try:
            status = polling(wf_name, 10, 18)
            if status:
                return (wf_name, status)
            status = polling(wf_name, 60, 1440)
        except Exception as exc:
            logger.debug("ARGO, ArgoWorkflow.execute(), while polling {}".format(type(exc)))
            logger.debug("ARGO, ArgoWorkflow.execute(), while polling {}".format(exc))
            raise exc
        return (wf_name, status)

    def exec_no_wait(self, context, wf_data={}):
        """
        Execute the workflow with given context and data, but do not wait for completion

        Args:
            context (ArgoWorkflowExeContext): context to execute the workflow in
            wf_data (dict, optional): data to be passed to workflow. Defaults to {}.

        Returns:
            dict: response of the api call as a json object
        """
        if wf_data:
            self._wf_def["spec"]["arguments"] = wf_data["arguments"]

        json_resp = context.client().run_workflow(self.wf_def)
        return json_resp

    @staticmethod
    def status(context, wf_name):
        """
        Query status of a workflow

        Args:
            context (ArgoWorkflowExeContext): context to perform the query
            wf_name (str): the workflow name returned from Argo server

        Returns:
            dict: {"complete": bool, "success": bool, "error": bool}
        """
        try:
            status = {
                "complete": None,
                "success": None,
                "error": None,
            }
            # get workflow
            json_obj = context.client().get_workflow(wf_name)

            # unknown state
            if "status" not in json_obj or "phase" not in json_obj["status"]:
                status["complete"] = False
                return status

            phase = json_obj["status"]["phase"]

            if phase == "Running":
                status["complete"] = False
                return status

            elif phase == "Succeeded":
                status["complete"] = True
                status["success"] = True

            elif phase == "Failed":
                status["complete"] = True
                status["success"] = False

            elif phase == "Error":
                status["complete"] = True
                status["success"] = False
                status["error"] = True

            return status
        except Exception as exc:
            # TODO
            raise exc

    @property
    def wf_def(self):
        """
        Workflow definition

        Returns:
            dict: workflow definition as JSON object
        """
        return self._wf_def

def _find_provider_dir(base_directory, provider_name, default_provider="default"):
    """
    Check if the provider workflow directory exists

    Args:
        base_directory (str): base directory for workflow files
        provider_name (str): provider name
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
                            if entry == provider_name]
        # try default provider if given provider dir does not exist
        if not provider_dirs and default_provider:
            provider_dirs = [entry for entry in os.listdir(base_directory)
                             if entry == default_provider]
        if not provider_dirs:
            raise ProviderWorkflowDirNotExist(provider_name)

        provider_dir = base_directory + "/" + provider_dirs[0]
        return provider_dir
    except OSError:
        raise BaseWorkflowDirNotExist(base_directory)

def _find_workflow_file(provider_dir_path, filename, provider_name):
    """
    Find the path of the workflow file, and check if the file exists

    Args:
        provider_dir_path (str): path to the provider workflow directory
        filename (str): workflow definition filename
        provider_name (str): provider name

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
            raise WorkflowFileNotExist(provider_name, filename)

        # construct path
        wf_file_path = provider_dir_path + "/" + wf_files[0]
        return wf_file_path
    except OSError:
        raise ProviderWorkflowDirNotExist(provider_name)

def argo_lookup_workflow(base_directory, filename, provider_name):
    """
    Lookup workflow by name and cloud provider

    Args:
        base_directory (str): base directory for workflow files
        filename (str): workflow filename
        provider_name (str): the provider name

    Raises:
        WorkflowFileNotYAML: unable to parse workflow definition file as YAML
        WorkflowFileNotExist: unable to open/read workflow definition file

    Returns:
        ArgoWorkflow: a workflow object if found, None otherwise
    """
    provider_dir_path = _find_provider_dir(base_directory, provider_name)
    wf_file_path = _find_workflow_file(provider_dir_path, filename, provider_name)

    try:
        # read workflow definition
        with open(wf_file_path, "r") as wf_file:
            wf_def = yaml.safe_load(wf_file.read())
    except yaml.YAMLError:
        raise WorkflowFileNotYAML(wf_file_path)
    except IOError:
        raise WorkflowFileNotExist(wf_file_path)

    return ArgoWorkflow(wf_def=wf_def)

def _read_argo_config(config_file_path=None):
    """
    Read configuration for Argo.
    Read from given path if specified, else read from path specified in the settings.

    Args:
        config_file_path (str, optional): path to the config file. will use the default one from the setting if None. Defaults to None.

    Raises:
        ArgoConfigFileNotExist: [description]
        ArgoConfigFileNotYAML: [description]
    """
    try:
        if not config_file_path:
            # path from settings
            config_file_path = settings.ARGO_CONFIG_FILE_PATH

        with open(settings.ARGO_CONFIG_FILE_PATH, "r") as config_file:
            config = yaml.safe_load(config_file.read())
            return config
    except IOError:
        raise ArgoConfigFileNotExist(config_file_path)
    except yaml.YAMLError:
        raise ArgoConfigFileNotYAML(config_file_path)

def argo_workflow_exec(workflow_filename, provider_name, workflow_data, config_file_path=None, wait=False):
    """
    Execute an specified Argo workflow.
    Find file based on provider.
    Pass argument to workflow.

    Args:
        workflow_filename (str): filename of the workflow
        provider_name (str): uuid of the provider
        workflow_data (dict): data to be passed to workflow as arguments
        config_file_path (str, optional): path to the config file. will use the default one from the setting if None. Defaults to None.
        wait (bool, optional): wait for workflow to complete. Defaults to False.

    Returns:
        str: workflow name returned by Argo server
    """
    try:
        # read configuration from file
        config = _read_argo_config(config_file_path=config_file_path)

        # find the workflow definition & construct workflow
        wf = argo_lookup_workflow(config["workflow_base_dir"], workflow_filename, provider_name)

        # construct workflow context
        context = ArgoWorkflowExeContext(config=config)

        # execute
        if wait:
            wf_name = wf.execute(context, workflow_data)
        else:
            wf_name = wf.exec_no_wait(context, workflow_data)
        return wf_name
    except Exception as exc:
        logger.exception("ARGO, argo_workflow_exec(), {} {}".format(type(exc), exc))
        raise exc
