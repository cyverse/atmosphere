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
        import atmosphere, os

        # ensure base dir for log dump exists
        log_dump_dir = os.path.abspath(os.path.join(
            os.path.dirname(atmosphere.__file__), "..", "logs", "argo"))
        if not os.path.isdir(log_dump_dir):
            os.makedirs(log_dump_dir)

        # log dump file for the workflow
        log_dump_file = os.path.join(log_dump_dir, wf_name + ".log")

        # find out what pods the workflow is consisted of
        json_resp = context.client().get_workflow(wf_name)
        pod_names = json_resp["status"]["nodes"].keys()

        with open(log_dump_file, "a+") as dump_file:
            dump_file.write("workflow {} has {} pods\n".format(wf_name, len(pod_names)))
            # dump logs for each pods
            for pod_name in pod_names:
                logs_lines = context.client().get_log_for_pod_in_workflow(wf_name, pod_name, container_name="main")
                dump_file.write("\n\pod {}:\n".format(pod_name))
                dump_file.writelines(logs_lines)
            logger.debug(("ARGO, log dump for workflow {} at: {}\n").format(wf_name, log_dump_file))

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
