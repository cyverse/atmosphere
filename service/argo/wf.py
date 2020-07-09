"""
Workflow
"""

import os
import json
import yaml
import time
from service.argo.common import ArgoContext
from service.argo.rest_api import ArgoAPIClient
from service.argo.exception import *
from django.conf import settings

from threepio import celery_logger as logger

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
            context (ArgoContext): context to execute the workflow in
            wf_data (dict, optional): data to be passed to workflow. Defaults to {}.

        Returns:
            (str, ArgoWorkflowStatus): workflow name and status of the workflow
        """
        json_resp = self.exec_no_wait(context, wf_data=wf_data)
        wf_name = json_resp["metadata"]["name"]

        try:
            status = ArgoWorkflow.polling(context, wf_name, 10, 18)
            if status.complete:
                return (wf_name, status)
            status = ArgoWorkflow.polling(context, wf_name, 60, 1440)
        except Exception as exc:
            logger.debug("ARGO, ArgoWorkflow.execute(), while polling {}".format(type(exc)))
            logger.debug("ARGO, ArgoWorkflow.execute(), while polling {}".format(exc))
            raise exc
        return (wf_name, status)

    def exec_no_wait(self, context, wf_data={}):
        """
        Execute the workflow with given context and data, but do not wait for completion

        Args:
            context (ArgoContext): context to execute the workflow in
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
            context (ArgoContext): context to perform the query
            wf_name (str): the workflow name returned from Argo server

        Returns:
            ArgoWorkflowStatus: status of workflow
        """
        try:
            # get workflow
            json_obj = context.client().get_workflow(wf_name)

            # unknown state
            if "status" not in json_obj or "phase" not in json_obj["status"]:
                return ArgoWorkflowStatus(complete=False)

            phase = json_obj["status"]["phase"]

            if phase == "Running":
                return ArgoWorkflowStatus(complete=False)

            elif phase == "Succeeded":
                return ArgoWorkflowStatus(complete=True, success=True)

            elif phase == "Failed":
                return ArgoWorkflowStatus(complete=True, success=False)

            elif phase == "Error":
                return ArgoWorkflowStatus(complete=True, success=False, error=True)

            return ArgoWorkflowStatus()
        except Exception as exc:
            # TODO
            raise exc

    @staticmethod
    def polling(context, wf_name, interval, repeat_count):
        """
        Polling the status of workflow, until the workflow is complete.
        This call will block as it is busy waiting.
        After a specified number of queries, the call will abort and return last status.

        Args:
            context (ArgoContext): context to perform the query
            wf_name (str): name of the workflow
            interval (int): interval(sec) in between query for status
            repeat_count (int): number of query for status to perform before abort

        Returns:
            ArgoWorkflowStatus: last status of the workflow
        """
        for _ in range(repeat_count):
            status = ArgoWorkflow.status(context, wf_name)
            if status.complete:
                return status
            time.sleep(interval)
        return status

    @staticmethod
    def dump_logs(context, wf_name):
        # find out what pods the workflow is consisted of
        json_resp = context.client().get_workflow(wf_name)
        pod_names  = json_resp["status"]["nodes"].keys()

        # dump logs for each pods
        for pod_name in pod_names:
            logs_lines = context.client().get_log_for_pod_in_workflow(wf_name, pod_name, container_name="main")
            logs = [line for line in logs_lines]
            logger.debug(("ARGO, workflow {}, pod {} logs:\n").format(wf_name, pod_name) + '\n'.join(logs))

    @property
    def wf_def(self):
        """
        Workflow definition

        Returns:
            dict: workflow definition as JSON object
        """
        return self._wf_def

class ArgoWorkflowStatus:
    """
    Status of a workflow
    """
    __slots__ = ["_complete", "_success", "_error"]
    def __init__(self, complete=None, success=None, error=None):
        """
        Args:
            complete (bool, optional): whether the workflow has completed
            success (bool, optional): whether the workflow has succeed
            error (bool, optional): whether the workflow has errored out
        """
        self._complete = complete
        self._success = success
        self._error = error

    @property
    def complete(self):
        """
        Returns:
            bool: whether the workflow has completed
        """
        return self._complete

    @property
    def success(self):
        """
        Returns:
            bool: whether the workflow has succeed
        """
        return self._success

    @property
    def error(self):
        """
        Returns:
            bool: whether the workflow has errored out
        """
        return self._error

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
        str: path to provider directory
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
        context = ArgoContext(config=config)

        # execute
        if wait:
            wf_name = wf.execute(context, workflow_data)
        else:
            wf_name = wf.exec_no_wait(context, workflow_data)
        return wf_name
    except Exception as exc:
        logger.exception("ARGO, argo_workflow_exec(), {} {}".format(type(exc), exc))
        raise exc
