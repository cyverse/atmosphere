import os

from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf.urls import patterns, url, include


from rest_framework.urlpatterns import format_suffix_patterns

from api.accounts import Account
from api.application import ApplicationSearch, ApplicationList, Application
from api.bookmark import  ApplicationBookmarkDetail, ApplicationBookmarkList
from api.email import Feedback, QuotaEmail, SupportEmail
from api.flow import Flow
from api.group import GroupList, Group
from api.identity_membership import IdentityMembershipList, IdentityMembership
from api.identity import IdentityList, Identity, IdentityDetailList
from api.instance import InstanceList, Instance,\
    InstanceAction, InstanceHistory
from api.machine import MachineList, Machine, MachineHistory,\
    MachineSearch, MachineVote, MachineIcon
from api.machine_request import MachineRequestList, MachineRequest,\
    MachineRequestStaffList, MachineRequestStaff
from api.machine_export import MachineExportList, MachineExport
from api.maintenance import MaintenanceRecordList, MaintenanceRecord
from api.meta import Meta, MetaAction
from api.notification import NotificationList
from api.occupancy import Occupancy, Hypervisor
from api.project import ProjectList, ProjectDetail
from api.project import ProjectInstanceList, ProjectInstanceExchange,\
        ProjectApplicationList, ProjectApplicationExchange,\
        ProjectVolumeList, ProjectVolumeExchange
from api.profile import Profile
from api.provider import ProviderList, Provider
from api.size import SizeList, Size
from api.hypervisor import HypervisorList, HypervisorDetail
from api.step import StepList, Step
from api.tag import TagList, Tag
from api.token import TokenEmulate
from api.user import UserManagement, User
from api.version import Version
from api.volume import VolumeSnapshot, VolumeSnapshotDetail, VolumeList, Volume

from authentication.decorators import atmo_valid_token_required
#Paste This for provider: provider\/(?P<provider_id>\\d+)
provider_specific = r"^provider/(?P<provider_id>\d+)"
#Paste this for identity: 
# /r'^provider\/(?P<provider_id>\\d+)\/identity\/(?P<identity_id>\
identity_specific = provider_specific + r"/identity/(?P<identity_id>\d+)"
user_match = "[A-Za-z0-9]+(?:[ _-][A-Za-z0-9]+)*)"

private_apis = patterns('',
    # E-mail API
    url(r'^email/feedback', Feedback.as_view()),
    url(r'^email/support', SupportEmail.as_view()),
    url(r'^email/request_quota[/]?$', QuotaEmail.as_view()),

    # TODO: Deprecate this if it isn't going to be used.
    # instance service (Calls from within the instance)
    url(r'^instancequery/', 'web.views.ip_request'),

    #File Retrieval:
    # static files
    url(r'^init_files/(?P<file_location>.*)$', 'web.views.get_resource'),

    #Project Related APIs
    url(r'project[/]?$',
        ProjectList.as_view(),
        name='project-list'),
    url(r'project/(?P<project_id>\d+)[/]?$',
        ProjectDetail.as_view(),
        name='project-detail'),
    url(r'project/(?P<project_id>\d+)/application[/]?$',
        ProjectApplicationList.as_view(),
        name='project-application-list'),
    url(r'project/(?P<project_id>\d+)/application/(?P<application_uuid>[a-zA-Z0-9-]+)[/]?$',
        ProjectApplicationExchange.as_view(),
        name='project-application-exchange'),
    url(r'project/(?P<project_id>\d+)/instance[/]?$',
        ProjectInstanceList.as_view(),
        name='project-instance-list'),
    url(r'project/(?P<project_id>\d+)/instance/(?P<instance_id>[a-zA-Z0-9-]+)[/]?$',
        ProjectInstanceExchange.as_view(),
        name='project-instance-exchange'),
    url(r'project/(?P<project_id>\d+)/volume[/]?$',
        ProjectVolumeList.as_view(),
        name='project-volume-list'),
    url(r'project/(?P<project_id>\d+)/volume/(?P<volume_id>[a-zA-Z0-9-]+)[/]?$',
        ProjectVolumeExchange.as_view(),
        name='project-volume-exchange'),





    url(r'^maintenance/(?P<record_id>\d+)[/]?$',
        MaintenanceRecord.as_view(),
        name='maintenance-record'),
    url(r'^notification[/]?$', NotificationList.as_view()),
    url(r'^token_emulate/(?P<username>.*)[/]?$', TokenEmulate.as_view()),

    #url(r'^user[/]?$', atmo_valid_token_required(UserManagement.as_view())),
    #url(r'^user/(?P<username>.*)[/]?$', User.as_view()),

    url(provider_specific + r'/occupancy[/]?$',
        Occupancy.as_view(), name='occupancy'),
    url(provider_specific + r'/hypervisor[/]?$',
        Hypervisor.as_view(), name='hypervisor'),

    #Application Bookmarks (Leave out until new UI Ready )
    url(r'^bookmark[/]?$',
        ApplicationBookmarkList.as_view(), name='bookmark-list'),

    url(r'^bookmark/application[/]?$',
        ApplicationBookmarkList.as_view(), name='bookmark-application-list'),

    url(r'^bookmark/application/(?P<app_uuid>[a-zA-Z0-9-]+)[/]?$',
        ApplicationBookmarkDetail.as_view(), name='bookmark-application'),


    #Machine Requests (Staff view)
    url(r'^request_image[/]?$',
        MachineRequestStaffList.as_view(), name='direct-machine-request-list'),
    url(r'^request_image/(?P<machine_request_id>\d+)[/]?$',
        MachineRequestStaff.as_view(), name='direct-machine-request-detail'),
    url(r'^request_image/(?P<machine_request_id>\d+)/(?P<action>.*)[/]?$',
        MachineRequestStaff.as_view(), name='direct-machine-request-action'),


    url(provider_specific + r'/account/(?P<username>([A-Za-z0-9]+(?:[ _-][A-Za-z0-9]+)*))[/]?$',
        Account.as_view(), name='account-management'),


    url(identity_specific + r'/image_export[/]?$',
        MachineExportList.as_view(), name='machine-export-list'),
    url(identity_specific + r'/image_export/(?P<machine_request_id>\d+)[/]?$',
        MachineExport.as_view(), name='machine-export'),

    url(identity_specific + r'/hypervisor[/]?$',
        HypervisorList.as_view(), name='hypervisor-list'),
    url(identity_specific + r'/hypervisor/(?P<hypervisor_id>\d+)[/]?$',
        HypervisorDetail.as_view(), name='hypervisor-detail'),

    url(identity_specific + r'/step[/]?$',
        StepList.as_view(), name='step-list'),
    url(identity_specific + r'/step/(?P<step_id>[a-zA-Z0-9-]+)[/]?$',
        Step.as_view(), name='step-detail'),



    #TODO: Uncomment when 'voting' feature is ready.
    url(identity_specific + r'/machine/(?P<machine_id>[a-zA-Z0-9-]+)/vote[/]?$',
        MachineVote.as_view(), name='machine-vote'),

    url(identity_specific + r'/meta[/]?$', Meta.as_view(), name='meta-detail'),
    url(identity_specific + r'/meta/(?P<action>.*)[/]?$',
        MetaAction.as_view(), name='meta-action'),

    url(identity_specific + r'/members[/]?$',
        IdentityMembershipList.as_view(), name='identity-membership-list'),
    url(identity_specific + r'/members/(?P<group_name>(%s)$' % user_match,
        IdentityMembership.as_view(), name='identity-membership-detail'),
)

public_apis = format_suffix_patterns(patterns(
    '',
    url(r'^profile[/]?$', Profile.as_view(), name='profile'),

    url(r'^group[/]?$', GroupList.as_view(), name='group-list'),
    url(r'^group/(?P<groupname>.*)[/]?$', Group.as_view()),

    url(r'^tag[/]?$', TagList.as_view(), name='tag-list'),
    url(r'^tag/(?P<tag_slug>.*)[/]?$', Tag.as_view()),

    url(r'^application[/]?$',
        ApplicationList.as_view(),
        name='application-list'),

    url(r'^application/search[/]?$',
        ApplicationSearch.as_view(),
        name='application-search'),
    url(r'^application/(?P<app_uuid>[a-zA-Z0-9-]+)[/]?$',
        Application.as_view(),
        name='application-detail'),

    url(r'^instance[/]?$', InstanceHistory.as_view(),
        name='instance-history'),

    url(identity_specific + r'/instance/'
        + '(?P<instance_id>[a-zA-Z0-9-]+)/action[/]?$',
        InstanceAction.as_view(), name='instance-action'),
    url(identity_specific + r'/instance/history[/]?$',
        InstanceHistory.as_view(), name='instance-history'),
    url(identity_specific + r'/instance/(?P<instance_id>[a-zA-Z0-9-]+)[/]?$',
        Instance.as_view(), name='instance-detail'),
    url(identity_specific + r'/instance[/]?$',
        InstanceList.as_view(), name='instance-list'),

    url(identity_specific + r'/size[/]?$',
        SizeList.as_view(), name='size-list'),
    url(identity_specific + r'/size/(?P<size_id>\d+)[/]?$',
        Size.as_view(), name='size-detail'),


    url(identity_specific + r'/volume[/]?$',
        VolumeList.as_view(), name='volume-list'),
    url(identity_specific + r'/volume/(?P<volume_id>[a-zA-Z0-9-]+)[/]?$',
        Volume.as_view(), name='volume-detail'),
    url(identity_specific + r'/volume_snapshot[/]?$',
        VolumeSnapshot.as_view(), name='volume-snapshot'),
    url(identity_specific + r'/volume_snapshot/(?P<snapshot_id>[a-zA-Z0-9-]+)[/]?$',
        VolumeSnapshotDetail.as_view(), name='volume-snapshot-detail'),


    url(identity_specific + r'/machine[/]?$',
        MachineList.as_view(), name='machine-list'),
    url(identity_specific + r'/machine/history[/]?$',
        MachineHistory.as_view(), name='machine-history'),
    url(identity_specific + r'/machine/search[/]?$',
        MachineSearch.as_view(), name='machine-search'),
    url(identity_specific + r'/machine/(?P<machine_id>[a-zA-Z0-9-]+)[/]?$',
        Machine.as_view(), name='machine-detail'),
    url(identity_specific + r'/machine/(?P<machine_id>[a-zA-Z0-9-]+)'
        + '/icon[/]?$', MachineIcon.as_view(), name='machine-icon'),

    url(provider_specific + r'/identity[/]?$', IdentityList.as_view(), name='identity-list'),
    url(identity_specific + r'[/]?$', Identity.as_view(), name='identity-detail'),

    url(r'^identity[/]?$', IdentityDetailList.as_view(),
        name='identity-detail-list'),
    url(r'^provider[/]?$', ProviderList.as_view(), name='provider-list'),
    url(r'^provider/(?P<provider_id>\d+)[/]?$',
        Provider.as_view(), name='provider-detail'),


    url(identity_specific + r'/request_image[/]?$',
        MachineRequestList.as_view(), name='machine-request-list'),
    url(identity_specific + r'/request_image/(?P<machine_request_id>\d+)[/]?$',
        MachineRequest.as_view(), name='machine-request'),


    url(identity_specific + r'/profile[/]?$',
        Profile.as_view(), name='profile-detail'),

    url(r'version[/]?$', Version.as_view()),
    url(r'^maintenance[/]?$',
        MaintenanceRecordList.as_view(),
        name='maintenance-record-list'),

))
urlpatterns = patterns('',
        url(r'^', include(private_apis,namespace="private_apis")))
urlpatterns += patterns('',
        url(r'^', include(public_apis,namespace="public_apis")))


