"""
Client to access Argo REST API
"""

import json
import requests
from threepio import celery_logger as logger
from service.argo.exception import ResponseNotJSON

try:
    from json import JSONDecodeError
except ImportError:
    # python2 does not has JSONDecodeError
    JSONDecodeError = ValueError

class ArgoAPIClient:
    """
    REST API Client for Argo.
    A thin layer of abstraction over Argo REST API endpoints
    """

    def __init__(self, api_host, port, k8s_token, wf_namespace, verify=True):
        """
        init the API client with all necessary credentials

        Args:
            api_host (str): hostname of where Argo server is hosted
            port (int): port of Argo server
            k8s_token (str): k8s token to authenticate with Argo server
            wf_namespace (str): k8s namespace used for the workflow
            verify (bool): verify SSL/TLS cert or not
        """
        self._host = api_host
        self._port = port
        self._base_url = "https://{}:{}".format(self._host, self._port)
        self._token = k8s_token
        self._namespace = wf_namespace
        self._verify = verify

    def get_workflow(self, wf_name, fields=""):
        """
        Endpoint for fetching a workflow

        Args:
            wf_name (str): name of the workflow
            fields (str): fields to be included in the response

        Returns:
            dict: response text as JSON object
        """
        api_url = "/api/v1/workflows/{}/{}"
        api_url = api_url.format(self._namespace, wf_name)
        if fields:
            api_url = "{}?fields={}".format(api_url, fields)

        json_resp = self._req("get", api_url)

        return json_resp

    def list_workflow(self):
        """
        Endpoint for fetching a list of workflows

        Returns:
            dict: response text as JSON object
        """
        api_url = "/api/v1/workflows/" + self._namespace

        json_resp = self._req("get", api_url)

        return json_resp

    def run_workflow(self, wf_json):
        """
        Endpoint for running a workflow

        Args:
            wf_json (dict): workflow definition as JSON object

        Returns:
            dict: response text as JSON object
        """
        api_url = "/api/v1/workflows/" + self._namespace

        json_data = {}
        json_data["namespace"] = self._namespace
        json_data["serverDryRun"] = False
        json_data["workflow"] = wf_json

        json_resp = self._req("post", api_url, json_data=json_data)

        return json_resp

    def get_log_for_pod_in_workflow(self, wf_name, pod_name, container_name="main"):
        """
        Get the logs of a pod in a workflow

        Args:
            wf_name (str): name of the workflow
            pod_name (str): name of the pod
            container_name (str, optional): name of the container. Defaults to "main".

        Returns:
            list: a list of lines of logs
        """
        api_url = "/api/v1/workflows/{}/{}/{}/log?logOptions.timestamps=true&logOptions.container={}"
        api_url = api_url.format(self._namespace, wf_name, pod_name, container_name)

        resp = self._req("get", api_url, json_resp=False)

        logs = []
        # each line is a json obj
        for line in resp.split("\n"):
            try:
                line = line.strip()
                if not line:
                    continue
                log_json = json.loads(line)
                if "result" not in log_json or "content" not in log_json["result"]:
                    continue
                logs.append(log_json["result"]["content"])
            except Exception:
                continue
        return logs

    def get_workflow_template(self, wf_temp_name):
        """
        fetch a workflow template by its name

        Args:
            wf_temp_name (str): name of the workflow template

        Returns:
            dict: response text as JSON object
        """
        api_url = "/api/v1/workflows-templates/{}/{}"
        api_url = api_url.format(self._namespace, wf_temp_name)

        json_resp = self._req("get", api_url)

        return json_resp

    def list_workflow_templates(self):
        """
        fetch a list of workflow templates

        Returns:
            dict: response text as JSON object
        """
        api_url = "/api/v1/workflows-templates/{}"
        api_url = api_url.format(self._namespace)

        json_resp = self._req("get", api_url)

        return json_resp

    def create_workflow_template(self, wf_temp_def_json):
        """
        create workflow template

        Args:
            wf_temp_def (dict): definition of the workflow template

        Returns:
            dict: response text as JSON object
        """
        api_url = "/api/v1/workflow-templates/" + self._namespace

        json_data = {}
        json_data["namespace"] = self._namespace
        json_data["template"] = wf_temp_def_json

        json_resp = self._req("post", api_url, json_data=json_data)

        return json_resp

    def update_workflow_template(self, wf_temp_name, wf_temp_def_json):
        """
        update workflow template with the given name

        Args:
            wf_temp_def (dict): definition of the workflow template

        Returns:
            dict: response text as JSON object
        """
        api_url = "/api/v1/workflow-templates/{}/{}".format(self._namespace, wf_temp_name)

        json_data = {}
        json_data["namespace"] = self._namespace
        json_data["template"] = wf_temp_def_json

        json_resp = self._req("put", api_url, json_data=json_data)

        return json_resp

    def submit_workflow_template(self, wf_temp_name, wf_param=[]):
        """
        submit a workflow template for execution with parameters.
        this will create a workflow.

        Args:
            wf_temp_name (str): name of the workflow template
            wf_param ([str]): list of parameters, in the form of ["NAME1=VAL1", "NAME2=VAL2"]

        Returns:
            dict: response text as JSON object
        """
        api_url = "/api/v1/workflows/{}/submit".format(self._namespace)

        json_data = {}
        json_data["namespace"] = self._namespace
        json_data["resourceKind"] = "WorkflowTemplate"
        json_data["resourceName"] = wf_temp_name
        json_data["submitOptions"] = {}
        json_data["submitOptions"]["parameters"] = wf_param

        json_resp = self._req("post", api_url, json_data=json_data)

        return json_resp

    def delete_workflow_template(self, wf_temp_name):
        """
        delete a workflow templates with given name

        Args:
            wf_temp_name (str): name of the workflow template

        Returns:
            dict: response text as JSON object
        """
        api_url = "/api/v1/workflow-templates/{}/{}"
        api_url = api_url.format(self._namespace, wf_temp_name)

        json_resp = self._req("delete", api_url)

        return json_resp

    def _req(self, method, url, json_data={}, additional_headers={}, json_resp=True):
        """
        send a request with given method to the given url

        Args:
            method (str): HTTP method
            url (str): api url to send the request to
            json_data (dict, optional): JSON payload. Defaults to None.
            additional_header (dict, optional): additional headers. Defaults to None.
            json_resp (bool, optional): if response is json. Defaults to True.

        Raises:
            ResponseNotJSON: raised when the response is not JSON
            HTTPError: requert failed

        Returns:
            dict: response text as JSON object
        """

        try:
            headers = {}
            headers["Host"] = self.host
            headers["Accept"] = "application/json;q=0.9,*/*;q=0.8"
            headers["Content-Type"] = "application/json"
            if self._token:
                headers["Authorization"] = "Bearer " + self._token

            if additional_headers:
                headers.update(additional_headers)

            full_url = self.base_url + url
            requests_func = _http_method(method)
            if json_data:
                resp = requests_func(full_url, headers=headers, json=json_data, verify=self.verify)
            else:
                resp = requests_func(full_url, headers=headers, verify=self.verify)
            resp.raise_for_status()
            if json_resp:
                return json.loads(resp.text)
            return resp.text
        except JSONDecodeError as exc:
            msg = "ARGO - REST API, {}, {}".format(type(exc), resp.text)
            logger.exception(msg)
            raise ResponseNotJSON("ARGO, Fail to parse response body as JSON")
        except requests.exceptions.HTTPError as exc:
            msg = "ARGO - REST API, {}, {}".format(type(exc), resp.text)
            logger.exception(msg)
            raise exc

    @property
    def host(self):
        """
        hostname of the Argo API Server.
        e.g. localhost

        Returns:
            str: hostname of the Argo API Server
        """
        return self._host

    @property
    def base_url(self):
        """
        base url for the Argo API Server.
        e.g. http://localhost:1234

        Returns:
            str: base url for the Argo API Server
        """
        return self._base_url

    @property
    def namespace(self):
        """
        k8s namespace used for the workflow

        Returns:
            str: k8s namespace
        """
        return self._namespace

    @property
    def verify(self):
        """
        whether to verify SSL/TLS cert of api host or not

        Returns:
            bool: whether to verify SSL/TLS cert of api host or not
        """
        return self._verify

def _http_method(method_str):
    """
    Return function for given HTTP Method from requests library

    Args:
        method_str (str): HTTP method, "get", "post", etc.

    Returns:
        function: requests.get, requests.post, etc. None if no match
    """
    if method_str == "get":
        return requests.get
    if method_str == "post":
        return requests.post
    if method_str == "delete":
        return requests.delete
    if method_str == "put":
        return requests.put
    if method_str == "options":
        return requests.options
    return None
