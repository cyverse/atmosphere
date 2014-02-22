"""
Atmosphere service exceptions.
"""


class HypervisorCapacityError(Exception):

    def __init__(self, hypervisor, message):
        self.hypervisor = hypervisor
        self.message = message
        super(HypervisorCapacityError, self).__init__(self.message)

class OverAllocationError(Exception):

    def __init__(self, wait_timedelta):
        self.wait_timedelta = wait_timedelta
        self.message = "Time allocation exceeded. "\
            "Wait %s before requesting new resources"\
            % (self.wait_timedelta)
        super(OverAllocationError, self).__init__(self.message)

    def __str__(self):
        return "%s" % (self.message, )


class OverQuotaError(Exception):

    def __init__(self, resource, requested, used, limit):
        self.message = "Quota exceeded: Requested %s %s but already used "\
                       "%s/%s %s."\
                       % (requested, resource, used, limit, resource)
        super(OverQuotaError, self).__init__(self.message)

    def __str__(self):
        return "%s" % (self.message, )


class DeviceBusyException(Exception):

    def __init__(self, mount_loc, process_list):
        proc_str = ''
        for proc_name, pid in process_list:
            proc_str += '\nProcess name:%s process id:%s' % (proc_name, pid)
        message = "Volume mount location is: %s\nRunning processes that"\
                  " are accessing that directory must be closed before "\
                  "unmounting. All offending processes names and IDs are "\
                  "listed below:%s" % (mount_loc, proc_str)
        self.message = message
        #Exception.__init__(self, message)
        super(DeviceBusyException, self).__init__(mount_loc, process_list)

    def __str__(self):
        return "%s:\n%s" % (self.message, repr(self.process_list))


class SizeNotAvailable(Exception):

    def __init__(self):
        message = "Size Not Available."
        super(SizeNotAvailable, self).__init__()

    def __str__(self):
        return "%s" % (self.message, )
