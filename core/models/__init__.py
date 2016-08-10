# -*- coding: utf-8 -*-
# flake8: noqa
"""
Collection of models
"""
from django.db.models import ObjectDoesNotExist
from core.models.allocation_strategy import Allocation, AllocationStrategy
from core.models.allocation_source import (
        AllocationSource, UserAllocationSource, UserAllocationSnapshot,
        InstanceAllocationSourceSnapshot, AllocationSourceSnapshot)
from core.models.application import Application, ApplicationMembership,\
    ApplicationScore, ApplicationBookmark, ApplicationThreshold
from core.models.application_tag import ApplicationTag
from core.models.application_version import ApplicationVersion, ApplicationVersionMembership
from core.models.cloud_admin import CloudAdministrator
from core.models.credential import Credential, ProviderCredential
from core.models.export_request import ExportRequest
from core.models.group import Group, IdentityMembership,\
    InstanceMembership, Leadership
from core.models.identity import Identity
from core.models.instance_tag import InstanceTag
from core.models.link import ExternalLink
from core.models.profile import UserProfile
from core.models.project import Project
from core.models.project_application import ProjectApplication
from core.models.project_link import ProjectExternalLink
from core.models.project_instance import ProjectInstance
from core.models.project_volume import ProjectVolume
from core.models.provider import (
    AccountProvider, ProviderType, PlatformType,
    Provider, ProviderInstanceAction, ProviderDNSServerIP,
    ProviderConfiguration
)
from core.models.license import LicenseType, License, ApplicationVersionLicense
from core.models.machine import ProviderMachine, ProviderMachineMembership
from core.models.machine_request import MachineRequest
from core.models.match import PatternMatch, MatchType
from core.models.maintenance import MaintenanceRecord
from core.models.instance import Instance
from core.models.instance_action import InstanceAction
from core.models.instance_history import InstanceStatus, InstanceStatusHistory
from core.models.instance_source import InstanceSource
from core.models.node import NodeController
from core.models.boot_script import ScriptType, BootScript, ApplicationVersionBootScript
from core.models.quota import Quota
from core.models.resource_request import ResourceRequest
from core.models.size import Size
from core.models.status_type import StatusType
from core.models.t import T
from core.models.tag import Tag
from core.models.template import (EmailTemplate, HelpLink)
from core.models.user import AtmosphereUser
from core.models.volume import Volume
from core.models.ssh_key import SSHKey

from core.models.event_table import EventTable
