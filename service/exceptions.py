# -*- coding: utf-8 -*-
"""
Atmosphere service exceptions.
"""

from ansible.errors import AnsibleError
from socket import error as socket_error
from rtwo.exceptions import ConnectionFailure, LibcloudInvalidCredsError, LibcloudBadResponseError


class ServiceException(Exception):
    """
    Base Service exception class
    """


class ActionNotAllowed(ServiceException):

    def __init__(self, message):
        self.message = message
        self.status_code = 409
        super(ActionNotAllowed, self).__init__()




class InstanceDoesNotExist(ServiceException):

    def __init__(self, instance_id):
        self.message = instance_id
        self.status_code = 404
        super(InstanceDoesNotExist, self).__init__()


class UnderThresholdError(ServiceException):

    def __init__(self, message):
        self.message = message
        self.status_code = 400
        super(UnderThresholdError, self).__init__()


class SecurityGroupNotCreated(ServiceException):

    def __init__(self):
        self.message = ("Gateway Timeout! Security Group(s) could not be "
                        "created. Please try again later")
        self.status_code = 504
        super(SecurityGroupNotCreated, self).__init__()

    def __str__(self):
        return "%s" % (self.message, )


class HypervisorCapacityError(ServiceException):

    def __init__(self, hypervisor, message):
        self.hypervisor = hypervisor
        self.message = message
        super(HypervisorCapacityError, self).__init__(self.message)


class OverAllocationError(ServiceException):

    def __init__(self, amount_exceeded):
        self.overage = amount_exceeded
        self.message = "Time allocation exceeded: Instance usage is over by "\
            "%s."\
            % (self.overage,)
        super(OverAllocationError, self).__init__(self.message)

    def __str__(self):
        return "%s" % (self.message, )


class OverQuotaError(ServiceException):

    def __init__(self, resource=None, requested=None,
                 used=None, limit=None, message=None):
        if not message:
            self.message = "Quota exceeded: Requested %s %s but already used "\
                           "%s/%s %s."\
                           % (requested, resource, used, limit, resource)
        else:
            self.message = message
        super(OverQuotaError, self).__init__(self.message)

    def __str__(self):
        return "%s" % (self.message, )


class DeviceBusyException(ServiceException):

    def __init__(self, mount_loc, process_list):
        proc_str = ''
        for proc_name, pid in process_list:
            proc_str += '\nProcess name:%s process id:%s' % (proc_name, pid)
        message = "Volume mount location is: %s\nRunning processes that"\
                  " are accessing that directory must be closed before "\
                  "unmounting. All offending processes names and IDs are "\
                  "listed below:%s" % (mount_loc, proc_str)
        self.message = message
        super(DeviceBusyException, self).__init__(mount_loc, process_list)

    def __str__(self):
        return "%s:\n%s" % (self.message, repr(self.process_list))


class SizeNotAvailable(ServiceException):

    def __init__(self):
        self.message = "Size Not Available."
        super(SizeNotAvailable, self).__init__()

    def __str__(self):
        return "%s" % (self.message, )


class VolumeDetachConflict(ServiceException):

    def __init__(self, message):
        self.message = message
        super(VolumeDetachConflict, self).__init__()

    def __str__(self):
        return "%s" % (self.message, )


class VolumeAttachConflict(ServiceException):

    def __init__(self, instance_id=None, volume_id=None, message=None):
        if not message:
            message = "Volume %s is still attached to instance %s"\
            % (volume_id, instance_id)
        self.message = message
        super(VolumeAttachConflict, self).__init__()

    def __str__(self):
        return "%s" % (self.message, )


class VolumeError(ServiceException):
    """
    Errors encountered during volume creation.
    """


class NotFound(ServiceException):
    """
    Exception raised when a resource cannot be found.
    """


class VolumeMountConflict(ServiceException):

    def __init__(self, instance_id, volume_id, extra=None):
        self.message = "Volume %s could not be auto-mounted to %s. %s"\
            " See Available Volumes -> Mounting a Volume "\
            " to learn how to mount the device manually"\
            % (volume_id, instance_id, "Reason:%s" % extra)
        super(VolumeMountConflict, self).__init__()

    def __str__(self):
        return "%s" % (self.message, )


class AnsibleDeployException(AnsibleError, ServiceException):
    pass
