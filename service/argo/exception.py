"""
Exceptions
"""

class ArgoBaseException(Exception):
    """
    Base exception for Argo related errors
    """

class ResponseNotJSON(ArgoBaseException):
    """
    Response of a HTTP request is not JSON
    """

class BaseWorkflowDirNotExist(ArgoBaseException):
    """
    Base directory for workflow files does not exist.
    """

class ProviderWorkflowDirNotExist(ArgoBaseException):
    """
    Workflow directory for the provider does not exist.
    """

class WorkflowFileNotExist(ArgoBaseException):
    """
    Workflow definition file (yaml file) does not exist
    """

class WorkflowFileNotYAML(ArgoBaseException):
    """
    Unable to parse workflow definition file as YAML
    """

class ArgoConfigFileNotExist(ArgoBaseException):
    """
    Configuration file for Argo does not exist
    """

class ArgoConfigFileNotYAML(ArgoBaseException):
    """
    Configuration file for Argo is not yaml
    """

class ArgoConfigFileError(ArgoBaseException):
    """
    Error in config file
    """

class WorkflowDataFileNotExist(ArgoBaseException):
    """
    Data file does not exist
    """

class WorkflowFailed(ArgoBaseException):
    """
    Workflow complete with "Failed"
    """

class WorkflowErrored(ArgoBaseException):
    """
    Workflow complete with "Error"
    """
