# flake8: noqa
from .allocation_source import AllocationSourceSerializer
from .boot_script import BootScriptSerializer
from .credential import CredentialSerializer
from .email_template import EmailTemplateSerializer
from .event import EventSerializer
from .group import GroupSerializer
from .help_link import HelpLinkSerializer
from .image_version import ImageVersionSerializer
from .image_version_boot_script import ImageVersionBootScriptSerializer
from .image_version_membership import ImageVersionMembershipSerializer
from .image_version_license import ImageVersionLicenseSerializer
from .identity import IdentitySerializer
from .identity_membership import IdentityMembershipSerializer
from .image import ImageSerializer
from .image_tag import ImageTagSerializer
from .image_bookmark import ImageBookmarkSerializer
from .instance_action import InstanceActionSerializer
from .instance_tag import InstanceTagSerializer
from .instance_history import InstanceStatusHistorySerializer
from .instance import InstanceSerializer
from .license import LicenseSerializer
from .link import ExternalLinkSerializer
from .maintenance_record import MaintenanceRecordSerializer
from .machine_request import (MachineRequestSerializer, UserMachineRequestSerializer)
from .project import ProjectSerializer
from .project_application import ProjectApplicationSerializer
from .project_link import ProjectExternalLinkSerializer
from .project_instance import ProjectInstanceSerializer
from .project_volume import ProjectVolumeSerializer
from .provider import (ProviderSerializer, ProviderTypeSerializer,
                       PlatformTypeSerializer)
from .provider_credential import ProviderCredentialSerializer
from .provider_machine import ProviderMachineSerializer
from .quota import QuotaSerializer, AllocationSerializer
from .resource_request import (
    ResourceRequestSerializer, UserResourceRequestSerializer)
from .reporting import InstanceReportingSerializer
from .size import SizeSerializer
from .ssh_key import SSHKeySerializer
from .status_type import StatusTypeSerializer
from .tag import TagSerializer
from .token import TokenSerializer
from .user import AdminUserSerializer, UserSerializer
from .volume import VolumeSerializer, UpdateVolumeSerializer
