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

    def __init__(self, wf_name):
        """Creates an ArgoWorkflow object from a workflow definition

        Args:
            wf_def (dict): workflow definition read/parsed from yaml
        """
        self._wf_name = wf_name
        self._last_status = None

    @staticmethod
    def create(context, wf_def, wf_data={}, lint=False):
        """
        Create a running workflow

        Args:
            context (ArgoContext): context to execute the workflow in
            wf_def (dict): workflow definition
            wf_data (dict, optional): workflow data to be pass along. Defaults to {}.
            lint (bool, optional): Whether to submit workflow definition for linting first. Defaults to False.

        Returns:
            ArgoWorkflow: ArgoWorkflow object created based on the returned json
        """
        if wf_data:
            wf_def = _populate_wf_data(wf_def, wf_data)

        json_resp = context.client().run_workflow(wf_def)
        wf_name = json_resp["metadata"]["name"]
        return ArgoWorkflow(wf_name)

    @staticmethod
    def create_n_watch(context, wf_def, wf_data={}):
        """
        Create a running workflow, and watch it until completion

        Args:
            context (ArgoContext): context to execute the workflow in
            wf_def (dict): workflow definition
            wf_data (dict, optional): data to be passed to workflow. Defaults to {}.

        Returns:
            (ArgoWorkflow, ArgoWorkflowStatus): workflow and status of the workflow
        """
        wf = ArgoWorkflow.create(context, wf_def, wf_data=wf_data)

        try:
            wf.watch(context, 10, 18)
            if wf.last_status.complete:
                return (wf, wf.last_status)
            wf.watch(context, 60, 1440)
        except Exception as exc:
            logger.debug("ARGO, ArgoWorkflow.create_n_watch(), while watching {}".format(type(exc)))
            logger.debug("ARGO, ArgoWorkflow.create_n_watch(), while watching {}".format(exc))
            raise exc
        return (wf, wf.last_status)

    def status(self, context):
        """
        Query status of a workflow

        Args:
            context (ArgoContext): context to perform the query

        Returns:
            ArgoWorkflowStatus: status of workflow
        """
        try:
            # get workflow
            json_obj = context.client().get_workflow(self._wf_name, fields="status.phase")

            # unknown state
            if "status" not in json_obj or "phase" not in json_obj["status"]:
                self._last_status = ArgoWorkflowStatus(complete=False)
                return self._last_status

            phase = json_obj["status"]["phase"]

            if phase == "Running":
                self._last_status = ArgoWorkflowStatus(complete=False)
                return self._last_status

            elif phase == "Succeeded":
                self._last_status = ArgoWorkflowStatus(complete=True, success=True)
                return self._last_status

            elif phase == "Failed":
                self._last_status = ArgoWorkflowStatus(complete=True, success=False)
                return self._last_status

            elif phase == "Error":
                self._last_status = ArgoWorkflowStatus(complete=True, success=False, error=True)
                return self._last_status

            return ArgoWorkflowStatus()
        except Exception as exc:
            # TODO
            raise exc

    def watch(self, context, interval, repeat_count):
        """
        Watch the status of workflow, until the workflow is complete.
        This call will block as it is busy waiting.
        After a specified number of queries, the call will abort and return last status.

        Args:
            context (ArgoContext): context to perform the query
            interval (int): interval(sec) in between query for status
            repeat_count (int): number of query for status to perform before abort

        Returns:
            ArgoWorkflowStatus: last status of the workflow
        """
        for _ in range(repeat_count):
            status = self.status(context)
            if status.complete:
                return status
            time.sleep(interval)
        return status

    def dump_logs(self, context, log_dir):
        """
        Dump logs of the workflow into the log directory provided.
        Separate log file for each pods/steps in the workflow, each with the filename of {{pod_name}}.log

        Args:
            context (ArgoContext): context used to fetch the logs
            log_dir (str): directory to dump logs into
        """
        # find out what pods the workflow is consisted of
        json_resp = context.client().get_workflow(self.wf_name)
        pod_names = json_resp["status"]["nodes"].keys()

        # dump logs in separate files for each pods
        for pod_name in pod_names:

            filename = "{}.log".format(pod_name)
            log_file_path = os.path.join(log_dir, filename)

            with open(log_file_path, "a+") as dump_file:
                dump_file.write("workflow {} has {} pods\n".format(self.wf_name, len(pod_names)))
                logs_lines = context.client().get_log_for_pod_in_workflow(self.wf_name, pod_name, container_name="main")
                dump_file.write("\n\pod {}:\n".format(pod_name))
                dump_file.writelines(logs_lines)
            logger.debug(("ARGO, log dump for workflow {}, pod {} at: {}\n").format(self.wf_name, pod_name, log_file_path))

    @property
    def wf_name(self):
        """
        Returns:
            str: name of the workflow
        """
        return self._wf_name

    @property
    def last_status(self):
        """
        Returns:
            ArgoWorkflowStatus: last known status of the workflow
        """
        return self._last_status

    @property
    def wf_def(self, context, fetch=True):
        """
        Definition of the workflow, will fetch if absent

        Args:
            context (ArgoContext): Argo context
            fetch (bool, optional): whether to fetch or not if present. Defaults to True.
        """
        if self._wf_def and not fetch:
            return self._wf_def
        self._wf_def = context.client().get_workflow(self._wf_name, fields="-status")
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

def _populate_wf_data(wf_def, wf_data):
    """
    Populate the workflow data in the workflow definition

    Args:
        wf_def (dict): workflow definition
        wf_data (dict): workflow data to be populated into workflow definition

    Returns:
        dict: workflow definition with the workflow data populated
    """
    if not wf_data["arguments"]:
        return wf_def
    if not wf_def["spec"]["arguments"]:
        wf_def["spec"]["arguments"] = {}

    if "parameters" in wf_data["arguments"]:
        wf_def["spec"]["arguments"]["parameters"] = wf_data["arguments"]["parameters"]
    if "artifacts" in wf_data["arguments"]:
        wf_def["spec"]["arguments"]["artifacts"] = wf_data["arguments"]["artifacts"]

    return wf_def
