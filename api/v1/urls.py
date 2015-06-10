from django.conf.urls import patterns, url, include

from rest_framework.urlpatterns import format_suffix_patterns

from api.v1 import views
# Regex matching you'll use everywhere..
id_match = '\d+'
uuid_match = '[a-zA-Z0-9-]+'
user_match = '[A-Za-z0-9]+(?:[ _-][A-Za-z0-9]+)*'

# Paste This for provider: provider\/(?P<provider_uuid>\\d+)
provider_specific = r'^provider/(?P<provider_uuid>%s)' % uuid_match
# Paste this for identity:
# /r'^provider\/(?P<provider_uuid>\\d+)\/identity\/(?P<identity_uuid>\
identity_specific = provider_specific +\
                    r'/identity/(?P<identity_uuid>%s)' % uuid_match

urlpatterns = format_suffix_patterns(patterns(
    '',
    # E-mail API
    url(r'^email/feedback', views.Feedback.as_view()),
    url(r'^email/support', views.SupportEmail.as_view()),
    url(r'^email/request_quota$', views.QuotaEmail.as_view()),

    # TODO: Deprecate this if it isn't going to be used.
    # instance service (Calls from within the instance)
    url(r'^instancequery/', 'web.views.ip_request'),

    # File Retrieval:
    # static files
    url(r'^init_files/(?P<file_location>.*)$', 'web.views.get_resource'),
    # boot_script Related APIs
    url(r'^boot_script$',
        views.BootScriptList.as_view(),
        name='boot_script_list'),
    url(r'^boot_script/(?P<script_id>%s)$' % (id_match,),
        views.BootScript.as_view(),
        name='boot_script'),

    # Project Related APIs
    url(r'^project$',
        views.ProjectList.as_view(),
        name='project-list'),

    url(r'^project/null$',
        views.NoProjectList.as_view(),
        name='empty-project-list'),
    url(r'^project/null/application$',
        views.NoProjectApplicationList.as_view(),
        name='empty-project-application-list'),
    url(r'^project/null/instance$',
        views.NoProjectInstanceList.as_view(),
        name='empty-project-instance-list'),
    url(r'^project/null/volume$',
        views.NoProjectVolumeList.as_view(),
        name='empty-project-volume-list'),

    url(r'^project/(?P<project_uuid>%s)$' % uuid_match,
        views.ProjectDetail.as_view(),
        name='project-detail'),
    url(r'^project/(?P<project_uuid>%s)/application$' % uuid_match,
        views.ProjectApplicationList.as_view(),
        name='project-application-list'),
    url(r'^project/(?P<project_uuid>%s)/application/(?P<application_uuid>%s)$'
        % (uuid_match, uuid_match),
        views.ProjectApplicationExchange.as_view(),
        name='project-application-exchange'),
    url(r'^project/(?P<project_uuid>%s)/instance$' % (uuid_match,),
        views.ProjectInstanceList.as_view(),
        name='project-instance-list'),
    url(r'^project/(?P<project_uuid>%s)/instance/(?P<instance_id>%s)$'
        % (uuid_match, uuid_match),
        views.ProjectInstanceExchange.as_view(),
        name='project-instance-exchange'),
    url(r'^project/(?P<project_uuid>%s)/volume$' % (uuid_match,),
        views.ProjectVolumeList.as_view(),
        name='project-volume-list'),
    url(r'^project/(?P<project_uuid>%s)/volume/(?P<volume_id>%s)$'
        % (uuid_match, uuid_match),
        views.ProjectVolumeExchange.as_view(),
        name='project-volume-exchange'),

    url(r'^maintenance/(?P<record_id>%s)$' % (id_match,),
        views.MaintenanceRecord.as_view(),
        name='maintenance-record'),
    url(r'^notification$', views.NotificationList.as_view()),
    url(r'^token_emulate/(?P<username>.*)$', views.TokenEmulate.as_view()),

    url(provider_specific + r'/occupancy$',
        views.Occupancy.as_view(), name='occupancy'),
    url(provider_specific + r'/hypervisor$',
        views.Hypervisor.as_view(), name='hypervisor'),

    url(r'^bookmark$',
        views.ApplicationBookmarkList.as_view(), name='bookmark-list'),
    url(r'^bookmark/application$',
        views.ApplicationBookmarkList.as_view(), name='bookmark-application-list'),
    url(r'^bookmark/application/(?P<app_uuid>%s)$' % uuid_match,
        views.ApplicationBookmarkDetail.as_view(), name='bookmark-application'),

    url(identity_specific + r'/image_export$',
        views.ExportRequestList.as_view(), name='machine-export-list'),
    url(identity_specific + r'/image_export/(?P<machine_request_id>%s)$'
        % (id_match,), views.ExportRequest.as_view(), name='machine-export'),

    url(identity_specific + r'/hypervisor$',
        views.HypervisorList.as_view(), name='hypervisor-list'),
    url(identity_specific + r'/hypervisor/(?P<hypervisor_id>%s)$'
        % (id_match,), views.HypervisorDetail.as_view(), name='hypervisor-detail'),

    url(identity_specific + r'/step$',
        views.StepList.as_view(), name='step-list'),
    url(identity_specific + r'/step/(?P<step_id>%s)$' % uuid_match,
        views.Step.as_view(), name='step-detail'),

    url(identity_specific + r'/machine/(?P<machine_id>%s)/vote$' % uuid_match,
        views.MachineVote.as_view(), name='machine-vote'),

    url(identity_specific + r'/meta$', views.Meta.as_view(), name='meta-detail'),
    url(identity_specific + r'/meta/(?P<action>.*)$',
        views.MetaAction.as_view(), name='meta-action'),

    url(identity_specific + r'/members$',
        views.IdentityMembershipList.as_view(), name='identity-membership-list'),
    url(identity_specific + r'/members/(?P<group_name>%s)$' % user_match,
        views.IdentityMembership.as_view(), name='identity-membership-detail'),
    #
    # Public api
    #
    url(r'^profile$', views.Profile.as_view(), name='profile'),

    url(r'^group$', views.GroupList.as_view(), name='group-list'),
    url(r'^group/(?P<groupname>.*)$', views.Group.as_view()),

    url(r'^tag$', views.TagList.as_view(), name='tag-list'),
    url(r'^tag/(?P<tag_slug>.*)$', views.Tag.as_view()),

    url(r'^application$',
        views.ApplicationList.as_view(),
        name='application-list'),

    url(r'^application/search$',
        views.ApplicationSearch.as_view(),
        name='application-search'),
    url(r'^application/(?P<app_uuid>%s)$' % uuid_match,
        views.Application.as_view(),
        name='application-detail'),
    # ApplicationThreshold Related APIs
    url(r'^application/(?P<app_uuid>%s)/threshold$' % uuid_match,
        views.ApplicationThresholdDetail.as_view(),
        name='threshold-detail'),

    url(r'^instance_history$', views.InstanceHistory.as_view(),
        name='instance-history'),
    url(r'^instance_history/'
        '(?P<instance_id>%s)$' % uuid_match, views.InstanceHistoryDetail.as_view(),
        name='instance-history'),
    url(r'^instance_history/(?P<instance_id>%s)/' % uuid_match +
        'status_history$', views.InstanceStatusHistoryDetail.as_view(),
        name='instance-history'),

    url(identity_specific + r'/instance/'
        '(?P<instance_id>%s)/tag$' % uuid_match,
        views.InstanceTagList.as_view(), name='instance-tag-list'),
    url(identity_specific + r'/instance/'
        '(?P<instance_id>%s)/tag/(?P<tag_slug>.*)$' % uuid_match,
        views.InstanceTagDetail.as_view(), name='instance-tag-detail'),
    url(identity_specific + r'/instance/'
        '(?P<instance_id>%s)/action$' % uuid_match,
        views.InstanceAction.as_view(), name='instance-action'),
    url(identity_specific + r'/instance/(?P<instance_id>%s)$' % uuid_match,
        views.Instance.as_view(), name='instance-detail'),
    url(identity_specific + r'/instance$',
        views.InstanceList.as_view(), name='instance-list'),

    url(r'^instance_action/$',
        views.InstanceActionList.as_view(),
        name='instance-action-list'),
    url(r'^instance_action/(?P<action_id>%s)$' % (id_match,),
        views.InstanceActionDetail.as_view(),
        name='instance-action-detail'),

    url(identity_specific + r'/size$',
        views.SizeList.as_view(), name='size-list'),
    url(identity_specific + r'/size/(?P<size_id>%s)$' % (id_match,),
        views.Size.as_view(), name='size-detail'),


    url(identity_specific + r'/volume$',
        views.VolumeList.as_view(), name='volume-list'),
    url(identity_specific + r'/volume/(?P<volume_id>%s)$' % uuid_match,
        views.Volume.as_view(), name='volume-detail'),
    url(identity_specific + r'/boot_volume(?P<volume_id>%s)?$' % uuid_match,
        views.BootVolume.as_view(), name='boot-volume'),

    url(identity_specific + r'/volume_snapshot$',
        views.VolumeSnapshot.as_view(), name='volume-snapshot'),
    url(identity_specific + r'/volume_snapshot/(?P<snapshot_id>%s)$'
        % uuid_match,
        views.VolumeSnapshotDetail.as_view(), name='volume-snapshot-detail'),

    url(identity_specific + r'/machine$',
        views.MachineList.as_view(), name='machine-list'),
    url(identity_specific + r'/machine/history$',
        views.MachineHistory.as_view(), name='machine-history'),
    url(identity_specific + r'/machine/search$',
        views.MachineSearch.as_view(), name='machine-search'),
    url(identity_specific + r'/machine/(?P<machine_id>%s)$' % uuid_match,
        views.Machine.as_view(), name='machine-detail'),
    url(identity_specific + r'/machine/(?P<machine_id>%s)/license$'
        % uuid_match, views.MachineLicense.as_view(), name='machine-license'),
    url(identity_specific + r'/machine/(?P<machine_id>%s)' % uuid_match +
        '/icon$', views.MachineIcon.as_view(), name='machine-icon'),

    url(provider_specific + r'/identity$', views.IdentityList.as_view(),
        name='identity-list'),
    url(identity_specific + r'$', views.Identity.as_view(),
        name='identity-detail'),

    url(r'^credential$', views.CredentialList.as_view(),
        name='credential-list'),
    url(r'^credential/(?P<identity_uuid>%s)$' % (uuid_match,),
        views.CredentialDetail.as_view(), name='credential-detail'),

    url(r'^identity$', views.IdentityDetailList.as_view(),
        name='identity-detail-list'),
    url(r'^identity/(?P<identity_uuid>%s)$' % (uuid_match,),
        views.IdentityDetail.as_view(),
        name='identity-detail'),
    url(r'^provider$', views.ProviderList.as_view(), name='provider-list'),
    url(r'^provider/(?P<provider_uuid>%s)$' % uuid_match,
        views.Provider.as_view(), name='provider-detail'),


    url(identity_specific + r'/request_image$',
        views.MachineRequestList.as_view(), name='machine-request-list'),
    url(identity_specific + r'/request_image/(?P<machine_request_id>%s)$'
        % (uuid_match,), views.MachineRequest.as_view(), name='machine-request'),


    url(identity_specific + r'/profile$',
        views.Profile.as_view(), name='profile-detail'),

    url(r'^allocation$',
        views.AllocationList.as_view(), name='allocation-list'),
    url(r'^allocation/(?P<quota_id>%s)$' % (id_match,),
        views.AllocationDetail.as_view(), name='quota-detail'),

    url(r'^quota$',
        views.QuotaList.as_view(), name='quota-list'),
    url(r'^quota/(?P<quota_id>%s)$' % (id_match,),
        views.QuotaDetail.as_view(), name='quota-detail'),


    url(r'^version$', views.Version.as_view()),
    url(r'^maintenance$',
        views.MaintenanceRecordList.as_view(),
        name='maintenance-record-list'),

    url(r'^license$',
        views.LicenseList.as_view(),
        name='license-list'),

    url(r'^license/(?P<license_id>%s)$' % uuid_match,
        views.License.as_view(),
        name='license-detail'),

    url(r'^monitoring$',
        views.MonitoringList.as_view(),
        name='monitoring-list'),

    url(r'^cloud_admin_imaging_request$',
        views.CloudAdminImagingRequestList.as_view(),
        name='cloud-admin-imaging-request-list'),
    url(r'^cloud_admin_imaging_request/(?P<machine_request_id>%s)$'
        % (id_match,),
        views.CloudAdminImagingRequest.as_view(),
        name='cloud-admin-imaging-request-detail'),
    url(r'^cloud_admin_imaging_request/'
        '(?P<machine_request_id>%s)/(?P<action>\w)$'
        % (id_match,),
        views.CloudAdminImagingRequest.as_view(),
        name='cloud-admin-imaging-request-detail'),

    url(r'^cloud_admin_account_list/$',
        views.CloudAdminAccountList.as_view(),
        name='cloud-admin-account-list'),
    url(r'^cloud_admin_account_list/(?P<username>%s)$'
        % (user_match,),
        views.CloudAdminAccount.as_view(),
        name='cloud-admin-account-detail'),
    url(r'^cloud_admin_instance_action/$',
        views.CloudAdminInstanceActionList.as_view(),
        name='cloud-admin-instance-action-list'),

    url(r'^cloud_admin_instance_action/'
        '(?P<provider_instance_action_id>%s)$' % (id_match,),
        views.CloudAdminInstanceAction.as_view(),
        name='cloud-admin-instance-action-detail'),

    url(identity_specific + r'/export_request$',
        views.ExportRequestList.as_view(), name='export-request-list'),
    url(identity_specific + r'/export_request/'
        '(?P<export_request_id>%s)$' % (id_match,),
        views.ExportRequest.as_view(), name='export-request'),

    url(identity_specific + r'/hypervisor$',
        views.HypervisorList.as_view(), name='hypervisor-list'),
    url(identity_specific + r'/hypervisor/'
        '(?P<hypervisor_id>%s)$' % (id_match,),
        views.HypervisorDetail.as_view(), name='hypervisor-detail'),

    url(identity_specific + r'/step$',
        views.StepList.as_view(), name='step-list'),
    url(identity_specific + r'/step/(?P<step_id>%s)$' % uuid_match,
        views.Step.as_view(), name='step-detail'),

    url(identity_specific + r'/machine/(?P<machine_id>%s)/vote$' % uuid_match,
        views.MachineVote.as_view(), name='machine-vote'),

    url(identity_specific + r'/meta$', views.Meta.as_view(), name='meta-detail'),
    url(identity_specific + r'/meta/(?P<action>.*)$',
        views.MetaAction.as_view(), name='meta-action'),

    url(identity_specific + r'/members$',
        views.IdentityMembershipList.as_view(), name='identity-membership-list'),
    url(identity_specific + r'/members/(?P<group_name>%s)$' % user_match,
        views.IdentityMembership.as_view(), name='identity-membership-detail')))
