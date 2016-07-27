from dateutil.relativedelta import relativedelta
from uuid import uuid4

import unittest

import pytz

from django.test import TestCase
from django.utils.timezone import datetime

from core.tests.helpers import CoreProviderMachineHelper, CoreMachineRequestHelper, CoreInstanceHelper
from service.machine import process_machine_request


class CoreMachineRequestTestCase(unittest.TestCase):

    """
    Add here any specific assertions to a 'MachineRequest' test case
    """
    # Super-helpful private methods

    def _new_instance_of(self, machine, start_date):
        # Create an instance of this machine
        instance_helper = CoreInstanceHelper(
            "Mock Instance", uuid4(),
            start_date, machine=machine)
        instance = instance_helper.to_core_instance()
        return instance

    def _process_new_fork_request(
            self,
            machine,
            new_name,
            new_version,
            uuid_suffix,
            fork_date=None):
        if not fork_date:
            fork_date = self.start_time
        instance = self._new_instance_of(machine, fork_date)
        # Create a MachineRequest for newly created Instance
        new_app_request_helper = CoreMachineRequestHelper(
            new_name, fork_date, new_version, True, instance)
        new_app_request = new_app_request_helper.to_core_machine_request()
        process_machine_request(new_app_request, 'machine-%s' % uuid_suffix,
                                update_cloud=False)
        new_machine = new_app_request.new_machine
        return new_machine

    def _process_new_update_request(
            self,
            machine,
            new_name,
            new_version,
            uuid_suffix,
            update_date=None):
        if not update_date:
            update_date = self.start_time
        instance = self._new_instance_of(machine, update_date)
        update_request_helper = CoreMachineRequestHelper(
            new_name, update_date, new_version, False, instance)
        core_request = update_request_helper.to_core_machine_request()
        process_machine_request(core_request, 'machine-%s' % uuid_suffix,
                                update_cloud=False)
        new_machine = core_request.new_machine
        return new_machine

    # Custom assertions
    def assertMachineVersionEquals(self, machine, version_test):
        self.assertEqual(machine.version, version_test)

    def assertApplicationNameEquals(self, machine, name_test):
        self.assertEqual(machine.application.name, name_test)


class TestVersionAndForking(CoreMachineRequestTestCase):

    def setUp(self):
        self.start_time = datetime(2015, 1, 1, tzinfo=pytz.utc)

        provider_machine_helper = CoreProviderMachineHelper(
            'First machine', 'machine-1', 'openstack', self.start_time)
        self.machine_1 = provider_machine_helper.to_core_machine()

        self.instance_helper = CoreInstanceHelper(
            "test_instance", "1234-1234-1234-1234",
            self.start_time, machine=self.machine_1)
        self.instance_1 = self.instance_helper.to_core_instance()
        pass

    def test_single_version_updating(self):
        """
        This test meant to represent which rules will succed/fail as
        'acceptable' versions. Currently, all version strings are acceptable.
        As these rules change, the tests will change/grow..
        """
        provider_machine_helper = CoreProviderMachineHelper(
            'Test Versioning',
            'machine-version-1',
            'openstack',
            self.start_time)
        machine_1 = provider_machine_helper.to_core_machine()
        machine_1.update_version('1')
        self.assertMachineVersionEquals(machine_1, '1')
        machine_1.update_version('1.2.1')
        self.assertMachineVersionEquals(machine_1, '1.2.1')
        machine_1.update_version('one-two-two')
        self.assertMachineVersionEquals(machine_1, 'one-two-two')
        machine_1.update_version('man-bear-pig')
        self.assertMachineVersionEquals(machine_1, 'man-bear-pig')
        pass

    def test_update_then_fork(self):
        provider_machine_helper = CoreProviderMachineHelper(
            'New Machine', 'new-machine-1', 'openstack', self.start_time)
        machine_1 = provider_machine_helper.to_core_machine()
        machine_2 = self._process_new_update_request(
            machine_1,
            "New Name, Same Version",
            "2.0",
            2)
        self.assertApplicationNameEquals(machine_2, "New Name, Same Version")
        self.assertMachineVersionEquals(machine_2, "2.0")
        machine_3 = self._process_new_fork_request(
            machine_2,
            "Totally different",
            "1.0",
            3)
        self.assertApplicationNameEquals(machine_3, "Totally different")
        self.assertMachineVersionEquals(machine_3, "1.0")
        pass

    def test_complex_fork_tree(self):
        # Boot strap the first machine
        provider_machine_helper = CoreProviderMachineHelper(
            'Complex Fork Test-New Machine',
            'new-machine-1234', 'openstack', self.start_time)
        machine_1 = provider_machine_helper.to_core_machine()
        machine_2 = self._process_new_update_request(
            machine_1, machine_1.application.name, "2.0", 2)
        self.assertApplicationNameEquals(machine_2, machine_1.application.name)
        self.assertMachineVersionEquals(machine_2, "2.0")

        machine_3 = self._process_new_update_request(
            machine_1, machine_1.application.name, "3.0", 3)
        self.assertApplicationNameEquals(machine_3, machine_1.application.name)
        self.assertMachineVersionEquals(machine_3, "3.0")

        machine_4 = self._process_new_update_request(
            machine_1, machine_1.application.name, "4.0", 4)
        self.assertApplicationNameEquals(machine_4, machine_1.application.name)
        self.assertMachineVersionEquals(machine_4, "4.0")
        self.assertApplicationNameEquals(machine_1, machine_4.application.name)

        fork_level_2 = self._process_new_fork_request(
            machine_2, "I am not machine 2", "1.0.0", 5)
        self.assertNotEqual(fork_level_2.application.name,
                            machine_2.application.name)
        update_fork_2 = self._process_new_update_request(
            fork_level_2, "not machine 2, but an update", "2.0.0", 6)
        self.assertApplicationNameEquals(
            fork_level_2,
            "not machine 2, but an update")
        self.assertApplicationNameEquals(
            update_fork_2,
            "not machine 2, but an update")
        self.assertMachineVersionEquals(fork_level_2, "1.0.0")
        self.assertMachineVersionEquals(update_fork_2, "2.0.0")

        fork_level_3 = self._process_new_fork_request(
            machine_3, "I am different from machine 3", "3.0.5", 7)
        self.assertNotEqual(fork_level_3.application.name,
                            machine_3.application.name)
        update_fork_3 = self._process_new_update_request(
            fork_level_3, fork_level_3.application.name, "3.0.6", 8)
        self.assertApplicationNameEquals(
            fork_level_3,
            "I am different from machine 3")
        self.assertApplicationNameEquals(
            update_fork_3,
            "I am different from machine 3")
        self.assertMachineVersionEquals(fork_level_3, "3.0.5")
        self.assertMachineVersionEquals(update_fork_3, "3.0.6")

        pass
