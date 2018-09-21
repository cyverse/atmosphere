from django.test import TestCase

import service.exceptions


class ExceptionTest(TestCase):
    def setUp(self):
        pass

    def test_device_busy_exception(self):
        mount_point = '/vol1'
        process_list = [('/bin/bash', 1067), ('/bin/vim', 2129)]

        new_exception = service.exceptions.DeviceBusyException(
            mount_point, process_list
        )
        expected_message = 'Volume mount location is: /vol1\nRunning processes that are accessing that directory ' \
                           'must be closed before unmounting. All offending processes names and IDs are listed ' \
                           'below:\nProcess name:/bin/bash process id:1067\nProcess name:/bin/vim process id:2129'
        self.assertEqual(new_exception.message, expected_message)

        expected_str = "Volume mount location is: /vol1\nRunning processes that are accessing that directory must be " \
                       "closed before unmounting. All offending processes names and IDs are listed below:\n" \
                       "Process name:/bin/bash process id:1067\nProcess name:/bin/vim process id:2129:\n" \
                       "[('/bin/bash', 1067), ('/bin/vim', 2129)]"
        self.assertEqual(str(new_exception), expected_str)
