from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import unittest

from dateutil.relativedelta import relativedelta
from django.utils.timezone import datetime, timedelta
import pytz

from rest_framework import status
from core.models import Allocation, Application, AtmosphereUser, Group,\
        Identity, IdentityMembership, \
        Instance, InstanceStatus, InstanceStatusHistory,\
        Provider,ProviderType, PlatformType, ProviderMembership, \
        ProviderMachine, Size, Quota
from core.fields import VersionNumber
#Create an instance
#build identical instance status history timings and try to add them
#It should fail and force you to do 'the right thing only'


class CoreInstanceTestCase(unittest.TestCase):

    def _get_history_manager(self, instance, *query_args, **query_kwargs):
        """
        Return instance history list
        """
        if not query_args and not query_kwargs:
            return instance.instancestatushistory_set.all()
        return instance.instancestatushistory_set.filter(*query_args, **query_kwargs)

    def assertZeroHistory(self, instance):
        """
        Assert that the instance has ZERO history
        """
        history_list = self._get_history_manager(instance)
        self.assertTrue(len(history_list) == 0)
        return self

    def assertNoActiveHistory(self, instance):
        """
        Assert that the instance has ZERO 'active' history
        """
        history_list = self._get_history_manager(instance, end_date=None)
        self.assertTrue(len(history_list) == 0)
        return self

    def assertOneActiveHistory(self, instance):
        """
        Assert that the instance has only ONE history
        """
        history_list = self._get_history_manager(instance, end_date=None)
        self.assertTrue(len(history_list) == 1)
        return self

class CoreStatusHistoryHelper(object):

    def __init__(self, instance, start_date, status_name='active', size_name='small'):
        self._init_sizes(instance.provider_machine.provider)
        self.instance = instance
        self.status_name = status_name
        self.set_size(size_name)
        self.set_start_date(start_date)

    def first_transaction(self):
        history = InstanceStatusHistory.create_history(
                self.status_name, self.instance, self.size, self.start_date)
        history.save()
        return history

    def new_transaction(self):
        return InstanceStatusHistory.transaction(
                self.status_name, self.instance, self.size, self.start_date)

    def _init_sizes(self, provider):
        size_params = [
                #name, alias, CPU, MEM, DISK/ROOT
                ('1', 'tiny', 1, 1024*2, 0),
                ('2', 'small', 2, 1024*4, 0),
                ('3', 'medium', 4, 1024*8, 0),
                ('4', 'large', 8, 1024*16, 0),
                ]
        self.AVAILABLE_SIZES = {}
        for s_params in size_params:
            core_size = Size.objects.get_or_create(
                    name=s_params[0], alias=s_params[1],
                    cpu=s_params[2], mem=s_params[3],
                    disk=s_params[4], root=s_params[4],
                    provider=provider)[0]
            self.AVAILABLE_SIZES[s_params[1]] = core_size


    def set_start_date(self, start_date):
        self.start_date = start_date

    def set_size(self, size_name):
        if size_name not in self.AVAILABLE_SIZES:
            raise ValueError("Size:%s not found in AVAILABLE_SIZES"
                    % size_name)
        self.size = self.AVAILABLE_SIZES[size_name]

class CoreInstanceHelper(object):

    def __init__(self, name, provider_alias, start_date,
            provider='openstack', machine='ubuntu', username='mock_user'):
        self.name = name
        self.provider_alias = provider_alias
        self.start_date = start_date
        #Mock Provider and dependencies..
        self._init_providers()
        self.set_provider(provider)
        #Mock the User, Identity, and dependencies..
        identity_member = self._new_mock_identity_member(username)
        self.identity = identity_member.identity
        self.user = self.identity.created_by
        self._init_provider_machines()
        self.set_machine(machine)

    def set_provider(self, provider):
        if provider not in self.AVAILABLE_PROVIDERS:
            raise ValueError(
                "The test provider specified '%s' is not a valid provider"
                % provider)
        self.provider = self.AVAILABLE_PROVIDERS[provider]


    def set_machine(self, machine):
        if machine not in self.AVAILABLE_MACHINES:
            raise ValueError(
                "The test machine specified '%s' is not a valid machine"
                % machine)
        self.machine = self.AVAILABLE_MACHINES[machine]

    def to_core_instance(self):
        return Instance.objects.get_or_create(
                name=self.name, provider_alias=self.provider_alias,
                provider_machine=self.machine, ip_address='1.2.3.4',
                created_by=self.user, created_by_identity=self.identity,
                token='unique-test-token-%s' % self.name,
                password='password',
                shell=False, start_date=self.start_date)[0]

    def _init_providers(self):
        kvm = PlatformType.objects.get_or_create(
                name='KVM')[0]
        openstack_type = ProviderType.objects.get_or_create(
                name='OpenStack')[0]
        openstack = Provider.objects.get_or_create(
                location="iPlant Cloud - Tucson",
                virtualization=kvm,
                type=openstack_type, public=True)[0]
        openstack_workshop = Provider.objects.get_or_create(
                location="iPlant Cloud - Workshop",
                virtualization=kvm,
                type=openstack_type, public=True)[0]
        self.AVAILABLE_PROVIDERS = {
            "openstack": openstack,
            "workshop": openstack_workshop
        }

    def _new_mock_identity_member(self, username):
        #Mock a user and an identity..
        mock_user = AtmosphereUser.objects.get_or_create(
                username=username)[0]
        mock_group = Group.objects.get_or_create(
                name=username)[0]
        mock_prov_member = ProviderMembership.objects.get_or_create(
                provider=self.provider, member=mock_group)[0]
        mock_identity = Identity.objects.get_or_create(
                created_by=mock_user,
                provider=self.provider)[0]
        mock_allocation = Allocation.default_allocation()
        mock_quota = Quota.default_quota()
        mock_identity_member = IdentityMembership.objects.get_or_create(
                identity=mock_identity, member=mock_group,
                allocation=mock_allocation, quota=mock_quota)[0]
        return mock_identity_member

    def _init_provider_machines(self):
        #Mock a machine and its dependencies..
        app = Application.objects.get_or_create(
                name='Ubuntu',
                description='', created_by=self.user,
                created_by_identity=self.identity,
                uuid='1234-ubuntu-mock-APP')[0]
        ubuntu = ProviderMachine.objects.get_or_create(
                application=app, provider=self.provider,
                created_by=self.user, created_by_identity=self.identity,
                identifier='1234-ubuntu-mock-machine',
                version=VersionNumber.string_to_version('1.0'))[0]

        app = Application.objects.get_or_create(
                name='CentOS',
                description='', created_by=self.user,
                created_by_identity=self.identity,
                uuid='1234-centos-mock-APP')[0]
        centos = ProviderMachine.objects.get_or_create(
                application=app, provider=self.provider,
                created_by=self.user, created_by_identity=self.identity,
                identifier='1234-centos-mock-machine',
                version=VersionNumber.string_to_version('1.0'))[0]
        self.AVAILABLE_MACHINES = {
            "ubuntu": ubuntu,
            "centos": centos,
        }


class TestInstanceStatusHistory(CoreInstanceTestCase):
    def setUp(self):
        self.history_swap_every = relativedelta(minutes=30)
        self.start_time = self.begin_history = datetime(2015, 1, 1, tzinfo=pytz.utc)
        self.terminate_time = datetime(2015,1,8, tzinfo=pytz.utc)
        self.instance_helper = CoreInstanceHelper(
                "test_instance", "1234-1234-1234-1234", self.start_time)
        
    def test_growing_history(self):
        """
        * Create an instance
        * Fill it with history
          * active/suspended every 30m for 1 week
        * Terminate it.

        Verify that AT MOST ONE history is 'un-end-dated'
        """
        self.instance_1 = self.instance_helper.to_core_instance()
        self.assertZeroHistory(self.instance_1)
        self.history_helper = CoreStatusHistoryHelper(self.instance_1, self.begin_history)
        #Create first history for instance
        first_history = self.history_helper.first_transaction()
        self.assertOneActiveHistory(self.instance_1)
        next_start = self.begin_history + self.history_swap_every
        suspended = False
        while next_start < self.terminate_time:
            self.history_helper.set_start_date(next_start)
            self.history_helper.status_name = \
                    'suspended' if suspended else 'active'
            next_history = self.history_helper.new_transaction()
            self.assertOneActiveHistory(self.instance_1)
            suspended = not suspended
            next_start = next_start + self.history_swap_every
        self.instance_1.end_date_all(self.terminate_time)
        self.assertNoActiveHistory(self.instance_1)



