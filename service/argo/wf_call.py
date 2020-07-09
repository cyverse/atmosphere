"""
Execute Argo Workflow
"""

import os
import json
import yaml
import time
from service.argo.common import ArgoContext, argo_lookup_yaml_file, read_argo_config
from service.argo.wf import ArgoWorkflow, ArgoWorkflowStatus
from service.argo.wf_temp import ArgoWorkflowTemplate
from service.argo.rest_api import ArgoAPIClient
from service.argo.exception import *
from django.conf import settings

from threepio import celery_logger as logger

def argo_workflow_exec(workflow_filename, provider_uuid, workflow_data, config_file_path=None, wait=False):
    """
    Execute an specified Argo workflow.
    Find file based on provider.
    Pass argument to workflow.

    Args:
        workflow_filename (str): filename of the workflow
        provider_uuid (str): uuid of the provider
        workflow_data (dict): data to be passed to workflow as arguments
        config_file_path (str, optional): path to the config file. will use the default one from the setting if None. Defaults to None.
        wait (bool, optional): wait for workflow to complete. Defaults to False.

    Returns:
        (str, ArgoWorkflowStatus): workflow name and status of the workflow
    """
    try:
        # read configuration from file
        config = read_argo_config(config_file_path=config_file_path, provider_uuid=provider_uuid)

        # find the workflow definition & construct workflow
        wf_def = argo_lookup_yaml_file(config["workflow_base_dir"], workflow_filename, provider_uuid)
        wf = ArgoWorkflow(wf_def)

        # construct workflow context
        context = ArgoContext(config=config)

        # execute
        if wait:
            result = wf.execute(context, workflow_data)
            return result
        else:
            wf_name = wf.exec_no_wait(context, workflow_data)
            return (wf_name, ArgoWorkflowStatus)
    except Exception as exc:
        logger.exception("ARGO, argo_workflow_exec(), {} {}".format(type(exc), exc))
        raise exc

def argo_wf_template_exec(wf_template_filename, provider_uuid, workflow_data, config_file_path=None, wait=False):
    """
    Execute an specified Argo workflow.
    Find file based on provider.
    Pass argument to workflow.

    Args:
        wf_template_filename (str): filename of the workflow
        provider_uuid (str): uuid of the provider
        workflow_data (dict): data to be passed to workflow as arguments
        config_file_path (str, optional): path to the config file. will use the default one from the setting if None. Defaults to None.
        wait (bool, optional): wait for workflow to complete. Defaults to False.

    Returns:
        (str, dict): workflow name and status of the workflow {"complete": bool, "success": bool, "error": bool}
    """
    try:
        # read configuration from file
        config = read_argo_config(config_file_path=config_file_path)

        # construct workflow context
        context = ArgoContext(config=config)

        # find the workflow definition
        wf_temp_def = argo_lookup_yaml_file(config["workflow_base_dir"], wf_template_filename, provider_uuid)

        # submit workflow template
        wf_temp = ArgoWorkflowTemplate.create(context, wf_temp_def)
        wf_name = wf_temp.execute(context, wf_param=workflow_data)

        # polling if needed
        if wait:
            status = ArgoWorkflow.polling(context, wf_name, 10, 18)
            if status.complete:
                return (wf_name, status)
            status = ArgoWorkflow.polling(context, wf_name, 60, 1440)
            return (wf_name, status)
        else:
            return (wf_name, {"complete": None, "success": None, "error": None})

    except Exception as exc:
        logger.exception("ARGO, argo_wf_template_exec(), {} {}".format(type(exc), exc))
        raise exc
