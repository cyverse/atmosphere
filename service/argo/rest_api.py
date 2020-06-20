"""
Client to access Argo REST API
"""

import requests
import json
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

    def get_workflow(self, wf_name):
        """
        Endpoint for fetching a workflow

        Args:
            wf_name (str): name of the workflow

        Returns:
            dict: response text as JSON object
        """
        api_url = "/api/v1/workflows/{}/{}"
        api_url = api_url.format(self._namespace, wf_name)

        json_resp = self._get_req(api_url)

        return json_resp

    def list_workflow(self):
        """
        Endpoint for fetching a list of workflows

        Returns:
            dict: response text as JSON object
        """
        api_url = "/api/v1/workflows/" + self._namespace

        json_resp = self._get_req(api_url)

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

        json_resp = self._post_req(api_url, json_data=json_data)

        return json_resp

    def _post_req(self, url, json_data=None, additional_header=None):
        """
        send a POST request to the given url with optional json payload and additional headers

        Args:
            url (str): api url to send the request to
            json_data (dict, optional): JSON payload. Defaults to None.
            additional_header (dict, optional): additional headers. Defaults to None.

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

            full_url = self.base_url + url
            resp = requests.post(full_url, headers=headers, json=json_data, verify=self.verify)
            resp.raise_for_status()
            json_obj = json.loads(resp.text)
        except JSONDecodeError as exc:
            msg = "ARGO - REST API, {}, {}".format(type(exc), resp.text)
            logger.exception(msg)
            raise ResponseNotJSON("ARGO, Fail to parse response body as JSON")
        except requests.exceptions.HTTPError as exc:
            msg = "ARGO - REST API, {}, {}".format(type(exc), resp.text)
            logger.exception(msg)
            raise exc
        return json_obj

    def _get_req(self, url):
        """
        send a GET request to the given url

        Args:
            url (str): api url to send the request to

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

            full_url = self.base_url + url
            resp = requests.get(full_url, headers=headers, verify=self.verify)
            resp.raise_for_status()
            json_obj = json.loads(resp.text)
        except JSONDecodeError as exc:
            msg = "ARGO - REST API, {}, {}".format(type(exc), resp.text)
            logger.exception(msg)
            raise ResponseNotJSON("ARGO, Fail to parse response body as JSON")
        except requests.exceptions.HTTPError as exc:
            msg = "ARGO - REST API, {}, {}".format(type(exc), resp.text)
            logger.exception(msg)
            raise exc
        return json_obj

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

