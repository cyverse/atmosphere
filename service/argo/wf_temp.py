"""
WorkflowTemplate
"""

import yaml
import json
from service.argo.common import ArgoContext

class ArgoWorkflowTemplate:
    """
    Abstraction of the WorkflowTemplate in Argo
    """

    def __init__(self, wf_temp_name):
        """
        Create a ArgoWorkflowTemplate object

        Args:
            wf_temp_name (str): name of the workflow template
        """
        self._name = wf_temp_name

    @classmethod
    def create(cls, context, wf_temp_def):
        """
        Create a WorkflowTemplate, and construct a ArgoWorkflowTemplate based off it

        Args:
            context (ArgoContext): context used to query the Argo Server
            wf_temp_def (dict): definition of the WorkflowTemplate

        Returns:
            ArgoWorkflowTemplate: constructed based off the WorkflowTemplate created
        """
        json_resp = context.client().create_workflow_template(wf_temp_def)
        name = json_resp["metadata"]["name"]
        return ArgoWorkflowTemplate(name)

    def fetch(self, context):
        """
        Fetch definition from Argo Server

        Args:
            context (ArgoContext): context used to query the Argo Server
        """
        json_resp = context.client().get_workflow_template(self.name)
        self._wf_temp_def = json_resp
        if "apiVersion" not in self._wf_temp_def:
            self._wf_temp_def["apiVersion"] = "argoproj.io/v1alpha1"
        if "kind" not in self._wf_temp_def:
            self._wf_temp_def["kind"] = "WorkflowTemplate"

    def update(self, context, wf_temp_def):
        """
        Update a WorkflowTemplate in Argo

        Args:
            context (ArgoContext): context of which the action should be executed in

        Returns:
            dict: json response
        """
        json_resp = context.client().create_workflow_template(self.wf_temp_def())
        return json_resp

    def execute(self, context, wf_param):
        """
        One-off submission of the workflow template, template is deleted after submission

        Args:
            context (ArgoContext): context of which the action should be executed in
            wf_param (dict): parameter to pass when submit the workflow template

        Returns:
            str: name of the workflow
        """
        # submit template
        json_resp = self.submit(context, wf_param)
        wf_name = json_resp["metadata"]["name"]

        # delete the template
        self.delete(context)
        return wf_name

    def submit(self, context, wf_param):
        """
        Submit the workflow template for execution, a workflow will be created as the result

        Args:
            context (ArgoContext): context of which the action should be executed in
            wf_param (dict): parameter to pass when submit the workflow

        Returns:
            dict: JSON response of the call
        """
        json_resp = context.client().submit_workflow_template(self.name, wf_param=wf_param)
        return json_resp

    def delete(self, context):
        """
        Delete the workflow template

        Args:
            context (ArgoContext): context of which the action should be executed in
        """
        context.client().delete_workflow_template(self.name)

    @property
    def wf_temp_def(self):
        """
        definition of the workflow template

        Returns:
            dict: definition
        """
        return self._wf_temp_def

    @property
    def name(self):
        """
        name of the workflow template

        Returns:
            str: name
        """
        return self._name


