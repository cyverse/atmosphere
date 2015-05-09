from core.models.credential import Credential, ProviderCredential
from core.models.cloud_admin import CloudAdministrator
from core.models.identity import Identity
from core.models.instance_tag import InstanceTag
from core.models.profile import UserProfile
from core.models.project import Project
from core.models.project_instance import ProjectInstance
from core.models.project_volume import ProjectVolume
from core.models.provider import AccountProvider, ProviderType, PlatformType,\
    Provider, ProviderInstanceAction, ProviderDNSServerIP
from core.models.license import LicenseType, License
from core.models.machine import ProviderMachine, ProviderMachineMembership
from core.models.match import PatternMatch, MatchType
from core.models.machine_request import MachineRequest
from core.models.export_request import ExportRequest
from core.models.maintenance import MaintenanceRecord
from core.models.instance import Instance, InstanceStatusHistory,\
    InstanceStatus, InstanceAction, InstanceSource
from core.models.node import NodeController
from core.models.post_boot import ScriptType, BootScript
from core.models.size import Size
from core.models.quota import Quota
from core.models.t import T
from core.models.tag import Tag
from core.models.user import AtmosphereUser
from core.models.volume import Volume
from core.models.version import ApplicationVersion
from core.models.group import Group, IdentityMembership,\
    InstanceMembership
from core.models.allocation_strategy import Allocation, AllocationStrategy
from core.models.step import Step
from core.models.request import AllocationRequest, QuotaRequest
from core.models.application import Application, ApplicationMembership,\
    ApplicationScore, ApplicationBookmark
from core.models.application_tag import ApplicationTag


def get_or_create(Model, *args, **kwargs):
    return Model.objects.get_or_create(*args, **kwargs)[0]


def create_machine_model(name, provider, provider_alias,
                         created_by, description):
    name = _get_valid_name(name, provider_alias)
    new_machine = get_or_create(Application,
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
