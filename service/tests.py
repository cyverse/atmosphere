from django.utils import unittest
from django.test import TestCase
from core.models import credential
import json

from atmosphere import settings

from service.accounts.openstack import AccountDriver as OSAccounts
from service.accounts.eucalyptus import AccountDriver as EucaAccounts

from core.models import ProviderCredential, ProviderType, Provider, Identity
from core.tests import create_euca_provider, create_os_provider


class ServiceTests(TestCase):

    '''
    Test service.*

    Methods to write:
    -----------------
    Instance Launch:
    * Identity_over_quota
    * invalid_provider_size
    * invalid_provider_machine
    * instance_launch_success
    * instance_launch_fail_*

    Instance Volume Attach:
    * Instance_terminated
    * Instance_suspended
    * Attach_failed
    * check_volume_failed
    * mount_failed

    Instance Action tests:
    * suspend success
    * stop success
    * reboot success
    * terminate

    '''

    def setUp(self):
        pass

    def tearDown(self):
        pass
