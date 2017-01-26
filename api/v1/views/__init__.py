# flake8: noqa
from api.v1.views.allocation import AllocationDetail, AllocationList, MonitoringList
from api.v1.views.cloud_admin import\
    CloudAdminImagingRequestList, CloudAdminImagingRequest,\
    CloudAdminAccountList, CloudAdminAccount,\
    CloudAdminInstanceActionList, CloudAdminInstanceAction
from api.v1.views.credential import CredentialList, CredentialDetail
from api.v1.views.email import Feedback, QuotaEmail, SupportEmail
from api.v1.views.group import GroupList, Group
from api.v1.views.identity_membership import IdentityMembershipList, IdentityMembership
from api.v1.views.identity import IdentityList, Identity, IdentityDetail,\
    IdentityDetailList
from api.v1.views.instance import InstanceList, Instance,\
    InstanceAction, InstanceHistory, InstanceHistoryDetail,\
    InstanceStatusHistoryDetail, InstanceTagList, InstanceTagDetail
from api.v1.views.instance_action import InstanceActionList, InstanceActionDetail
from api.v1.views.instance_query import ip_request
from api.v1.views.license import LicenseList, License
from api.v1.views.machine import MachineList, Machine, MachineHistory,\
    MachineSearch, MachineIcon, MachineLicense
from api.v1.views.machine_request import MachineRequestList, MachineRequest
from api.v1.views.export_request import ExportRequestList, ExportRequest
from api.v1.views.maintenance import MaintenanceRecordList, MaintenanceRecord
from api.v1.views.meta import Meta, MetaAction
from api.v1.views.notification import NotificationList
from api.v1.views.occupancy import Occupancy, Hypervisor
from api.v1.views.project import NoProjectList, NoProjectInstanceList,\
    NoProjectVolumeList
from api.v1.views.post_boot import BootScriptList, BootScript
from api.v1.views.project import ProjectList, ProjectDetail
from api.v1.views.project import ProjectInstanceList, ProjectInstanceExchange,\
    ProjectVolumeList, ProjectVolumeExchange
from api.v1.views.profile import Profile
from api.v1.views.provider import ProviderList, Provider
from api.v1.views.quota import QuotaDetail, QuotaList
from api.v1.views.size import SizeList, Size
from api.v1.views.hypervisor import HypervisorList, HypervisorDetail
from api.v1.views.tag import TagList, Tag
from api.v1.views.token import TokenEmulate
from api.v1.views.volume import BootVolume,\
    VolumeSnapshot, VolumeSnapshotDetail,\
    VolumeList, Volume
