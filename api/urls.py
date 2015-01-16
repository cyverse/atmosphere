import os

from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf.urls import patterns, url, include

from rest_framework.urlpatterns import format_suffix_patterns

from api.accounts import Account
from api.allocation import AllocationMembership
from api.application import ApplicationSearch, ApplicationList, Application,\
                            ApplicationThresholdDetail
from api.bookmark import  ApplicationBookmarkDetail, ApplicationBookmarkList
from api.email import Feedback, QuotaEmail, SupportEmail
from api.flow import Flow
from api.group import GroupList, Group
from api.identity_membership import IdentityMembershipList, IdentityMembership
from api.identity import IdentityList, Identity, IdentityDetail, IdentityDetailList
from api.instance import InstanceList, Instance,\
    InstanceAction, InstanceHistory, InstanceHistoryDetail,\
    InstanceStatusHistoryDetail, InstanceTagList, InstanceTagDetail
from api.machine import MachineList, Machine, MachineHistory,\
    MachineSearch, MachineVote, MachineIcon
from api.machine_request import MachineRequestList, MachineRequest,\
    MachineRequestStaffList, MachineRequestStaff
from api.machine_export import MachineExportList, MachineExport
from api.maintenance import MaintenanceRecordList, MaintenanceRecord
from api.meta import Meta, MetaAction
from api.notification import NotificationList
from api.occupancy import Occupancy, Hypervisor
from api.project import NoProjectList, NoProjectInstanceList,\
        NoProjectVolumeList, NoProjectApplicationList
from api.post_boot import BootScriptList, BootScript
from api.project import ProjectList, ProjectDetail
from api.project import ProjectInstanceList, ProjectInstanceExchange,\
        ProjectApplicationList, ProjectApplicationExchange,\
        ProjectVolumeList, ProjectVolumeExchange
from api.profile import Profile
from api.provider import ProviderList, Provider
from api.quota import QuotaMembership, QuotaList
from api.size import SizeList, Size
from api.hypervisor import HypervisorList, HypervisorDetail
from api.step import StepList, Step
from api.tag import TagList, Tag
from api.token import TokenEmulate
from api.user import UserManagement, User
from api.version import Version
from api.volume import BootVolume, \
        VolumeSnapshot, VolumeSnapshotDetail, \
        VolumeList, Volume

from authentication.decorators import atmo_valid_token_required
# Regex matching you'll use everywhere..
uuid_match = "[a-zA-Z0-9-]+"
user_match = "[A-Za-z0-9]+(?:[ _-][A-Za-z0-9]+)*)"

#Paste This for provider: provider\/(?P<provider_uuid>\\d+)
provider_specific = r"^provider/(?P<provider_uuid>%s)" % uuid_match
#Paste this for identity: 
# /r'^provider\/(?P<provider_uuid>\\d+)\/identity\/(?P<identity_uuid>\
identity_specific = provider_specific +\
                    r"/identity/(?P<identity_uuid>%s)" % uuid_match

private_apis = patterns('',
    # E-mail API
    url(r'^email/feedback', Feedback.as_view()),
    url(r'^email/support', SupportEmail.as_view()),
    url(r'^email/request_quota$', QuotaEmail.as_view()),

    # TODO: Deprecate this if it isn't going to be used.
    # instance service (Calls from within the instance)
    url(r'^instancequery/', 'web.views.ip_request'),

    #File Retrieval:
    # static files
    url(r'^init_files/(?P<file_location>.*)$', 'web.views.get_resource'),
    #boot_script Related APIs
    url(r'boot_script$',
        BootScriptList.as_view(),
        name='boot_script_list'),
    url(r'boot_script/(?P<script_id>\d+)$',
        BootScript.as_view(),
        name='boot_script'),

    #Project Related APIs
    url(r'project$',
        ProjectList.as_view(),
        name='project-list'),

    url(r'project/null$',
        NoProjectList.as_view(),
        name='empty-project-list'),
    url(r'project/null/application$',
        NoProjectApplicationList.as_view(),
        name='empty-project-application-list'),
    url(r'project/null/instance$',
        NoProjectInstanceList.as_view(),
        name='empty-project-instance-list'),
    url(r'project/null/volume$',
        NoProjectVolumeList.as_view(),
        name='empty-project-volume-list'),

    url(r"project/(?P<project_uuid>%s)$" % uuid_match,
        ProjectDetail.as_view(),
        name='project-detail'),
    url(r"project/(?P<project_uuid>%s)/application$" % uuid_match,
        ProjectApplicationList.as_view(),
        name='project-application-list'),
    url(r'project/(?P<project_uuid>%s)'
         '/application/(?P<application_uuid>%s)$'
         % (uuid_match,uuid_match),
        ProjectApplicationExchange.as_view(),
        name='project-application-exchange'),
    url(r'project/(?P<project_uuid>%s)/instance$' % (uuid_match,),
        ProjectInstanceList.as_view(),
        name='project-instance-list'),
    url(r'project/(?P<project_uuid>%s)/instance/(?P<instance_id>%s)$'
        % (uuid_match,uuid_match),
        ProjectInstanceExchange.as_view(),
        name='project-instance-exchange'),
    url(r'project/(?P<project_uuid>%s)/volume$' % (uuid_match,),
        ProjectVolumeList.as_view(),
        name='project-volume-list'),
    url(r'project/(?P<project_uuid>%s)/volume/(?P<volume_id>%s)$'
        % (uuid_match,uuid_match),
        ProjectVolumeExchange.as_view(),
        name='project-volume-exchange'),





    url(r'^maintenance/(?P<record_id>\d+)$',
        MaintenanceRecord.as_view(),
        name='maintenance-record'),
    url(r'^notification$', NotificationList.as_view()),
    url(r'^token_emulate/(?P<username>.*)$', TokenEmulate.as_view()),

    #url(r'^user$', atmo_valid_token_required(UserManagement.as_view())),
    #url(r'^user/(?P<username>.*)$', User.as_view()),

    url(provider_specific + r'/occupancy$',
        Occupancy.as_view(), name='occupancy'),
    url(provider_specific + r'/hypervisor$',
        Hypervisor.as_view(), name='hypervisor'),

    #Application Bookmarks (Leave out until new UI Ready )
    url(r'^bookmark$',
        ApplicationBookmarkList.as_view(), name='bookmark-list'),

    url(r'^bookmark/application$',
        ApplicationBookmarkList.as_view(), name='bookmark-application-list'),

    url(r'^bookmark/application/(?P<app_uuid>%s)$' % uuid_match,
        ApplicationBookmarkDetail.as_view(), name='bookmark-application'),



    #Machine Requests (Staff view)
    url(r'^request_image$',
        MachineRequestStaffList.as_view(), name='direct-machine-request-list'),
    url(r'^request_image/(?P<machine_request_id>\d+)$',
        MachineRequestStaff.as_view(), name='direct-machine-request-detail'),
    url(r'^request_image/(?P<machine_request_id>\d+)/(?P<action>.*)$',
        MachineRequestStaff.as_view(), name='direct-machine-request-action'),


    url(provider_specific + r'/account/(?P<username>([A-Za-z0-9]+(?:[ _-][A-Za-z0-9]+)*))$',
        Account.as_view(), name='account-management'),


    url(identity_specific + r'/image_export$',
        MachineExportList.as_view(), name='machine-export-list'),
    url(identity_specific + r'/image_export/(?P<machine_request_id>\d+)$',
        MachineExport.as_view(), name='machine-export'),

    url(identity_specific + r'/hypervisor$',
        HypervisorList.as_view(), name='hypervisor-list'),
    url(identity_specific + r'/hypervisor/(?P<hypervisor_id>\d+)$',
        HypervisorDetail.as_view(), name='hypervisor-detail'),

    url(identity_specific + r'/step$',
        StepList.as_view(), name='step-list'),
    url(identity_specific + r'/step/(?P<step_id>%s)$' % uuid_match,
        Step.as_view(), name='step-detail'),



    #TODO: Uncomment when 'voting' feature is ready.
    url(identity_specific + r'/machine/(?P<machine_id>%s)/vote$' % uuid_match,
        MachineVote.as_view(), name='machine-vote'),

    url(identity_specific + r'/meta$', Meta.as_view(), name='meta-detail'),
    url(identity_specific + r'/meta/(?P<action>.*)$',
        MetaAction.as_view(), name='meta-action'),

    url(identity_specific + r'/members$',
        IdentityMembershipList.as_view(), name='identity-membership-list'),
    url(identity_specific + r'/members/(?P<group_name>(%s)$' % user_match,
        IdentityMembership.as_view(), name='identity-membership-detail'),
)

public_apis = format_suffix_patterns(patterns(
    '',
    url(r'^profile$', Profile.as_view(), name='profile'),

    url(r'^group$', GroupList.as_view(), name='group-list'),
    url(r'^group/(?P<groupname>.*)$', Group.as_view()),

    url(r'^tag$', TagList.as_view(), name='tag-list'),
    url(r'^tag/(?P<tag_slug>.*)$', Tag.as_view()),

    url(r'^application$',
        ApplicationList.as_view(),
        name='application-list'),

    url(r'^application/search$',
        ApplicationSearch.as_view(),
        name='application-search'),
    url(r'^application/(?P<app_uuid>%s)$' % uuid_match,
        Application.as_view(),
        name='application-detail'),
    #ApplicationThreshold Related APIs
    url(r'^application/(?P<app_uuid>%s)/threshold$' % uuid_match,
        ApplicationThresholdDetail.as_view(),
        name='threshold-detail'),

    url(r'^instance_history$', InstanceHistory.as_view(),
        name='instance-history'),
    url(r'^instance_history/'
        '(?P<instance_id>%s)$' % uuid_match, InstanceHistoryDetail.as_view(),
        name='instance-history'),
    url(r'^instance_history/'
        + '(?P<instance_id>%s)/' % uuid_match
        + 'status_history$', InstanceStatusHistoryDetail.as_view(),
        name='instance-history'),

    url(identity_specific + r'/instance/'
        + '(?P<instance_id>%s)/tag$' % uuid_match,
        InstanceTagList.as_view(), name='instance-tag-list'),
    url(identity_specific + r'/instance/'
        + '(?P<instance_id>%s)/tag/(?P<tag_slug>.*)$' % uuid_match,
        InstanceTagDetail.as_view(), name='instance-tag-detail'),
    url(identity_specific + r'/instance/'
        + '(?P<instance_id>%s)/action$' % uuid_match,
        InstanceAction.as_view(), name='instance-action'),
    url(identity_specific + r'/instance/(?P<instance_id>%s)$' % uuid_match,
        Instance.as_view(), name='instance-detail'),
    url(identity_specific + r'/instance$',
        InstanceList.as_view(), name='instance-list'),

    url(identity_specific + r'/size$',
        SizeList.as_view(), name='size-list'),
    url(identity_specific + r'/size/(?P<size_id>\d+)$',
        Size.as_view(), name='size-detail'),


    url(identity_specific + r'/volume$',
        VolumeList.as_view(), name='volume-list'),
    url(identity_specific + r'/volume/(?P<volume_id>%s)$' % uuid_match,
        Volume.as_view(), name='volume-detail'),
    url(identity_specific + r'/boot_volume(?P<volume_id>%s)?$' % uuid_match,
        BootVolume.as_view(), name='boot-volume'),

    url(identity_specific + r'/volume_snapshot$',
        VolumeSnapshot.as_view(), name='volume-snapshot'),
    url(identity_specific + r'/volume_snapshot/(?P<snapshot_id>%s)$' % uuid_match,
        VolumeSnapshotDetail.as_view(), name='volume-snapshot-detail'),

    url(identity_specific + r'/machine$',
        MachineList.as_view(), name='machine-list'),
    url(identity_specific + r'/machine/history$',
        MachineHistory.as_view(), name='machine-history'),
    url(identity_specific + r'/machine/search$',
        MachineSearch.as_view(), name='machine-search'),
    url(identity_specific + r'/machine/(?P<machine_id>%s)$' % uuid_match,
        Machine.as_view(), name='machine-detail'),
    url(identity_specific + r'/machine/(?P<machine_id>%s)' % uuid_match
        + '/icon$', MachineIcon.as_view(), name='machine-icon'),

    url(provider_specific + r'/identity$', IdentityList.as_view(), name='identity-list'),
    url(identity_specific + r'$', Identity.as_view(), name='identity-detail'),

    url(r'^identity$', IdentityDetailList.as_view(),
        name='identity-detail-list'),
    url(r'^identity/(?P<identity_uuid>\d+)$', IdentityDetail.as_view(),
        name='identity-detail-list'),
    url(r'^provider$', ProviderList.as_view(), name='provider-list'),
    url(r'^provider/(?P<provider_uuid>%s)$' % uuid_match,
        Provider.as_view(), name='provider-detail'),


    url(identity_specific + r'/request_image$',
        MachineRequestList.as_view(), name='machine-request-list'),
    url(identity_specific + r'/request_image/(?P<machine_request_id>\d+)$',
        MachineRequest.as_view(), name='machine-request'),


    url(identity_specific + r'/profile$',
        Profile.as_view(), name='profile-detail'),

    url(identity_specific + r'/allocation$',
        AllocationMembership.as_view(), name='allocation'),


    url(identity_specific + r'/quota$',
        QuotaMembership.as_view(), name='quota'),

    url(r'^quota$',
        QuotaList.as_view(), name='quota-list'),


    url(r'version$', Version.as_view()),
    url(r'^maintenance$',
        MaintenanceRecordList.as_view(),
        name='maintenance-record-list'),

))
urlpatterns = patterns('',
        url(r'^', include(private_apis,namespace="private_apis")))
urlpatterns += patterns('',
        url(r'^', include(public_apis,namespace="public_apis")))


