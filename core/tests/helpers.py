"""
These helper classes are written to make it easier to write 'mock test cases'
for Core objects
"""
from core.models import Allocation, Application, AtmosphereUser, Group,\
    Identity, IdentityMembership, \
    Instance, InstanceStatusHistory,\
    MachineRequest, Provider, \
    ProviderType, PlatformType, \
    ProviderMachine, Size, Quota
from uuid import uuid4


def _new_providers():
    kvm = PlatformType.objects.get_or_create(
        name='KVM')[0]
    openstack_type = ProviderType.objects.get_or_create(
        name='OpenStack')[0]
    openstack = Provider.objects.get_or_create(
        location="Example OpenStack - Tucson",
        virtualization=kvm,
        type=openstack_type, public=True)[0]
    openstack_workshop = Provider.objects.get_or_create(
        location="Example OpenStack - Workshop",
        virtualization=kvm,
        type=openstack_type, public=True)[0]
    return {
        "openstack": openstack,
        "workshop": openstack_workshop
    }


def _new_mock_identity_member(username, provider):
    # Mock a user and an identity..
    mock_user = AtmosphereUser.objects.get_or_create(
        username=username)[0]
    mock_group = Group.objects.get_or_create(
        name=username)[0]
    mock_identity = Identity.objects.get_or_create(
        created_by=mock_user,
        provider=provider)[0]
    mock_allocation = Allocation.default_allocation()
    mock_quota = Quota.default_quota()
    mock_identity_member = IdentityMembership.objects.get_or_create(
        identity=mock_identity, member=mock_group,
        allocation=mock_allocation, quota=mock_quota)[0]
    return mock_identity_member


def _new_provider_machine(name, version, identifier, identity):
    app = Application.objects.get_or_create(
        name=name,
        description='Mock Test Application named %s' % name,
        created_by=identity.created_by, created_by_identity=identity,
        uuid=identifier)[0]
    machine = ProviderMachine.objects.get_or_create(
        application=app, provider=identity.provider,
        created_by=identity.created_by, created_by_identity=identity,
        identifier=identifier,
        version=version)[0]
    return machine


def _new_core_instance(name, alias, start_date, identity, machine=None):
    if not machine:
        machine = _new_provider_machine("Mock Machine", "1.0",
                                        uuid4(), identity)
    mock_user = identity.created_by

    return Instance.objects.get_or_create(
        name=name, provider_alias=alias,
        provider_machine=machine, ip_address='1.2.3.4',
        created_by=mock_user, created_by_identity=identity,
        token='unique-test-token-%s' % alias,
        password='password', shell=False, start_date=start_date)[0]


class CoreStatusHistoryHelper(object):

    def __init__(
            self,
            instance,
            start_date,
            status_name='active',
            size_name='small'):
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
            ('1', 'tiny', 1, 1024 * 2, 0),
            ('2', 'small', 2, 1024 * 4, 0),
            ('3', 'medium', 4, 1024 * 8, 0),
            ('4', 'large', 8, 1024 * 16, 0),
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
        # Mock Provider and dependencies..
        self.AVAILABLE_PROVIDERS = _new_providers()
        self.set_provider(provider)
        # Mock the User, Identity, and dependencies..
        identity_member = _new_mock_identity_member(
            username, self.provider)
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
        # If a provider machine is passed in, its always accepted
        if isinstance(machine, ProviderMachine):
            self.machine = machine
            return
        # If a string is passed in, it must match exactly
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

    def _init_provider_machines(self):
        # Mock a machine and its dependencies..
        app = Application.objects.get_or_create(
            name='Ubuntu',
            description='', created_by=self.user,
            created_by_identity=self.identity,
            uuid='1234-ubuntu-mock-APP')[0]
        ubuntu = ProviderMachine.objects.get_or_create(
            application=app, provider=self.provider,
            created_by=self.user, created_by_identity=self.identity,
            identifier='1234-ubuntu-mock-machine',
            version="1.0")[0]

        app = Application.objects.get_or_create(
            name='CentOS',
            description='', created_by=self.user,
            created_by_identity=self.identity,
            uuid='1234-centos-mock-APP')[0]
        centos = ProviderMachine.objects.get_or_create(
            application=app, provider=self.provider,
            created_by=self.user, created_by_identity=self.identity,
            identifier='1234-centos-mock-machine',
            version='1.0')[0]
        self.AVAILABLE_MACHINES = {
            "ubuntu": ubuntu,
            "centos": centos,
        }


class CoreProviderMachineHelper(object):

    def __init__(
            self,
            name,
            identifier,
            provider,
            start_date,
            username='mock_user'):
        self.name = name
        self.uuid = identifier
        # NOTE: Using 'identifier' as ProviderMachine and Application id's
        self.version = '1.0.0'
        self.start_date = start_date
        # Mock Provider and dependencies..
        self.AVAILABLE_PROVIDERS = _new_providers()
        self.set_provider(provider)
        # Mock the User, Identity, and dependencies..
        identity_member = _new_mock_identity_member(
            username, self.provider)
        self.identity = identity_member.identity
        self.user = self.identity.created_by

    def set_provider(self, provider):
        if provider not in self.AVAILABLE_PROVIDERS:
            raise ValueError(
                "The test provider specified '%s' is not a valid provider"
                % provider)
        self.provider = self.AVAILABLE_PROVIDERS[provider]

    def to_core_machine(self):
        self.machine = _new_provider_machine(self.name, self.version,
                                             self.uuid, self.identity)
        return self.machine


class CoreMachineRequestHelper(object):

    def __init__(self, new_application_name, start_date,
                 new_machine_version='1.0', new_machine_forked=True,
                 instance=None, provider='openstack', username='mock_user'):
        self.AVAILABLE_PROVIDERS = _new_providers()
        self.set_provider(provider)
        identity_member = _new_mock_identity_member(
            username, self.provider)
        self.identity = identity_member.identity
        self.user = self.identity.created_by
        self.forked = new_machine_forked
        if not instance:
            instance = _new_core_instance(
                "Mock Instance", uuid4(), start_date, self.identity, None)
        self.new_application_name = new_application_name
        self.new_machine_version = new_machine_version
        self.instance = instance
        self.start_date = start_date

    def set_provider(self, provider):
        if provider not in self.AVAILABLE_PROVIDERS:
            raise ValueError(
                "The test provider specified '%s' is not a valid provider"
                % provider)
        self.provider = self.AVAILABLE_PROVIDERS[provider]

    def to_core_machine_request(self):
        provider_machine = self.instance.provider_machine

        return MachineRequest.objects.get_or_create(
            instance=self.instance, status='pending',
            parent_machine=provider_machine,
            new_machine_provider=provider_machine.provider,
            new_application_name=self.new_application_name,
            new_machine_version=self.new_machine_version,
            new_machine_owner=self.user, new_machine_visibility='public',
            new_machine_forked=self.forked, start_date=self.start_date)[0]
