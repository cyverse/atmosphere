from core.models.credential import Credential, ProviderCredential
from core.models.identity import Identity
from core.models.profile import UserProfile
from core.models.provider import AccountProvider, ProviderType, PlatformType,\
    ProviderSize, Provider
from core.models.machine import ProviderMachine, ProviderMachineMembership
from core.models.machine_request import MachineRequest
from core.models.machine_export import MachineExport
from core.models.maintenance import MaintenanceRecord
from core.models.instance import Instance, InstanceStatusHistory,\
    InstanceStatus
from core.models.node import NodeController
from core.models.size import Size
from core.models.quota import Quota
from core.models.tag import Tag
from core.models.user import AtmosphereUser
from core.models.volume import Volume
from core.models.group import Group, ProviderMembership, IdentityMembership,\
    InstanceMembership
from core.models.allocation import Allocation
from core.models.step import Step
from core.models.application import Application, ApplicationMembership,\
    ApplicationScore


def get_or_create(Model, *args, **kwargs):
    return Model.objects.get_or_create(*args, **kwargs)[0]


def create_machine_model(name, provider, provider_alias,
                         created_by, description):
    name = _get_valid_name(name, provider_alias)
    new_machine = get_or_create(Machine,
                                name=name,
                                description=description,
                                created_by=created_by)
    provider_machine = get_or_create(ProviderMachine,
                                     machine=new_machine,
                                     provider=provider,
                                     identifier=provider_alias)
    return (new_machine, provider_machine)


def get_or_create_instance_model(name, provider, provider_alias,
                                 image_alias, ip_address, created_by):
    name = _get_valid_name(name, provider_alias)
    provider_machine = _get_or_create_provider_machine(
        provider,
        image_alias,
        created_by
    )
    return get_or_create(Instance,
                         name=name,
                         provider_alias=provider_alias,
                         provider_machine=provider_machine,
                         ip_address=ip_address,
                         created_by=created_by)


def _get_valid_name(name, alias):
    """
    Make sure there is a good default name if no name exists.
    """
    if name is None or len(name) == 0:
        name = alias
    return name


def _get_or_create_provider_machine(provider, image_alias, created_by):
    """
    Get or create a ProviderMachine.
    If ProviderMachine does not already exist
    create a new Machine and related ProviderMachine.
    """
    provider_machine = None
    filtered_machines = ProviderMachine.objects.filter(identifier=image_alias)
    if filtered_machines:
        provider_machine = filtered_machines[0]
    else:
        (created, provider_machine) = create_machine_model(
            None,
            provider,
            image_alias,
            created_by,
            "Created to support instanceModel")
    return provider_machine
