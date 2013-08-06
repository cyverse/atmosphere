class DeviceBusyException(Exception):

    def __init__(self, mount_loc, process_list):
        proc_str = ''
        for proc_name, pid in process_list:
            proc_str += '\nProcess name:%s process id:%s' % (proc_name, pid)
        message = "Volume mount location is: %s\nRunning processes that"\
        " are accessing that directory must be closed before unmounting."\
        " All offending processes names and IDs are listed below:%s"\
        % (mount_loc, proc_str)
        self.message = message
        #Exception.__init__(self, message)
        super(DeviceBusyException, self).__init__(mount_loc, process_list)

    def __str__(self):
        return "%s:\n%s" % (self.message, repr(self.process_list))
        

