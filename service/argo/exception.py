"""
Exceptions
"""

class ArgoBaseException(Exception):
    pass

class ResponseNotJSON(ArgoBaseException):
    """
    Response of a HTTP request is not JSON
    """
    pass

class BaseWorkflowDirNotExist(ArgoBaseException):
    """
    Base directory for workflow files does not exist.
    """
    pass

class ProviderWorkflowDirNotExist(ArgoBaseException):
    """
    Workflow directory for the provider does not exist.
    """
    pass

class WorkflowFileNotExist(ArgoBaseException):
    """
    Workflow definition file (yaml file) does not exist
    """
    pass

class WorkflowFileNotYAML(ArgoBaseException):
    """
    Unable to parse workflow definition file as YAML
    """
    pass

class ArgoConfigFileNotExist(ArgoBaseException):
    """
    Configuration file for Argo does not exist
    """
    pass

class ArgoConfigFileNotYAML(ArgoBaseException):
    """
    Configuration file for Argo is not yaml
    """
    pass

class WorkflowDataFileNotExist(ArgoBaseException):
    """
    Data file does not exist
    """
    pass
