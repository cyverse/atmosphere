# flake8: noqa
from .allocation_source import AllocationSourceSerializer
from .boot_script import BootScriptSerializer
from .email_template import EmailTemplateSerializer
from .group import GroupSerializer
from .help_link import HelpLinkSerializer
from .image_version import ImageVersionSerializer
from .image_version_boot_script import ImageVersionBootScriptSerializer
from .image_version_membership import ImageVersionMembershipSerializer
from .image_version_license import ImageVersionLicenseSerializer
from .identity import IdentitySerializer
from .identity_membership import IdentityMembershipSerializer
from .image import ImageSerializer
from .image_metric import ImageMetricSerializer
from .image_tag import ImageTagSerializer
from .image_access_list import ImageAccessListSerializer
from .image_bookmark import ImageBookmarkSerializer
from .instance_action import InstanceActionSerializer
from .instance_access import InstanceAccessSerializer, UserInstanceAccessSerializer
from .instance_playbook import InstancePlaybookHistorySerializer, InstancePlaybookSnapshotSerializer
from .instance_tag import InstanceTagSerializer
from .instance_history import InstanceStatusHistorySerializer
from .instance import InstanceSerializer
from .instance_allocation_source import InstanceAllocationSourceSerializer
from .instance_command import InstanceCommandSerializer
from .license import LicenseSerializer
from .link import ExternalLinkSerializer
from .maintenance_record import MaintenanceRecordSerializer
from .machine_request import (MachineRequestSerializer, UserMachineRequestSerializer)
from .pattern_match import PatternMatchSerializer
from .project import ProjectSerializer
from .project_application import ProjectApplicationSerializer
from .project_link import ProjectExternalLinkSerializer
from .project_instance import ProjectInstanceSerializer
from .project_volume import ProjectVolumeSerializer
from .provider import (ProviderSerializer, ProviderTypeSerializer,
                       PlatformTypeSerializer)
from .provider_machine import ProviderMachineSerializer
from .quota import QuotaSerializer
from .renewal_strategy import RenewalStrategySerializer
from .resource_request import (
    ResourceRequestSerializer, UserResourceRequestSerializer)
from .resource_request_actions import (
    ResourceRequest_UpdateQuotaSerializer)
from .reporting import InstanceReportingSerializer
from .size import SizeSerializer
from .ssh_key import SSHKeySerializer
from .status_type import StatusTypeSerializer
from .tag import TagSerializer
from .token import TokenSerializer
from .user import (
    AdminUserSerializer, UserSerializer)
from .user_allocation_source import UserAllocationSourceSerializer
from .volume import VolumeSerializer, UpdateVolumeSerializer
