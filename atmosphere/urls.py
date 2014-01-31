import os

from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf.urls import patterns, url, include


from rest_framework.urlpatterns import format_suffix_patterns

from api.accounts import Account
from api.application import ApplicationListNoAuth
from api.flow import Flow
from api.group import GroupList, Group
from api.identity_membership import IdentityMembershipList, IdentityMembership
from api.identity import IdentityList, Identity, IdentityDetailList
from api.instance import InstanceList, Instance,\
    InstanceAction, InstanceHistory
from api.machine import MachineList, Machine, MachineHistory,\
    MachineSearch
from api.machine_request import MachineRequestList, MachineRequest,\
    MachineRequestStaffList, MachineRequestStaff
from api.machine_export import MachineExportList, MachineExport
from api.maintenance import MaintenanceRecordList, MaintenanceRecord
from api.meta import Meta, MetaAction
from api.notification import NotificationList
from api.occupancy import Occupancy, Hypervisor
from api.profile import Profile
from api.provider import ProviderList, Provider
from api.size import SizeList, Size
from api.step import StepList, Step
from api.tag import TagList, Tag
from api.user import UserManagement, User
from api.version import Version
from api.volume import VolumeList, Volume

from authentication.decorators import atmo_valid_token_required

resources_path = os.path.join(os.path.dirname(__file__), 'resources')
mobile = os.path.join(os.path.dirname(__file__), 'mobile')
cloud2 = os.path.join(os.path.dirname(__file__), 'cf2')

admin.autodiscover()
urlpatterns = patterns(
    '',
    #Uncomment the next line to enable the admin control panel
    #admin logging, and admin user emulation
    url(r'^admin/emulate/$', 'web.views.emulate_request'),
    url(r'^admin/emulate/(?P<username>\w+)/$', 'web.views.emulate_request'),
    #url(r'^admin/logs/', 'web.views.logs'),
    url(r'^admin/', include(admin.site.urls)),

    # feedback
    url(r'^feedback', 'web.emails.feedback'),
    url(r'^api/v1/email_support', 'web.emails.email_support'),

    #v2 api url scheme
    url(r'^auth/$', 'authentication.views.token_auth', name='token-auth'),

    #This is a TEMPORARY url..
    #In v2 this is /api/provider/<id>/identity/<id>/instance/action
    #&& POST['action'] = request_image
    url(r'^api/v1/request_quota/$', 'web.emails.requestQuota'),

    # static files
    url(r'^init_files/(?P<file_location>.*)$', 'web.views.get_resource'),

    # Systemwide
    url(r'^resources/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': resources_path}),

    # instance service
    url(r'^instancequery/', 'web.views.ip_request'),

    # default
    url(r'^$', 'web.views.redirectApp'),

    #This URL validates the ticket returned after CAS login
    url(r'^CAS_serviceValidater',
        'authentication.protocol.cas.cas_validateTicket'),
    #This URL is a dummy callback
    url(r'^CAS_proxyCallback',
        'authentication.protocol.cas.cas_proxyCallback'),
    #This URL records Proxy IOU & ID
    url(r'^CAS_proxyUrl',
        'authentication.protocol.cas.cas_storeProxyIOU_ID'),

    url(r'^login/$', 'web.views.login'),
    url(r'^logout/$', 'web.views.logout'),
    url(r'^CASlogin/(?P<redirect>.*)$', 'authentication.cas_loginRedirect'),
    url(r'^application/$', 'web.views.app'),

    # Experimental UI
    # TODO: Rename to application when it launches
    url(r'^beta/', 'web.views.app_beta'),

    url(r'^partials/(?P<path>.*)$', 'web.views.partial'),
    url(r'^no_user/$', 'web.views.no_user_redirect'),

    ### DJANGORESTFRAMEWORK ###
    url(r'^api-auth/',
        include('rest_framework.urls', namespace='rest_framework'))
)

urlpatterns += format_suffix_patterns(patterns(
    '',
    url(r'api/v1/$', Meta.as_view()),
    url(r'api/v1/version/$', Version.as_view()),
    url(r'^api/v1/maintenance/$',
        MaintenanceRecordList.as_view(),
        name='maintenance-record-list'),
    url(r'^api/v1/maintenance/(?P<record_id>\d+)/$',
        MaintenanceRecord.as_view(),
        name='maintenance-record'),
    url(r'^api/v1/notification/$', NotificationList.as_view()),

    url(r'^api/v1/user/$', atmo_valid_token_required(UserManagement.as_view())),
    url(r'^api/v1/user/(?P<username>.*)/$', User.as_view()),
    url(r'^api/v1/profile/$', Profile.as_view(), name='profile'),
    url(r'^api/v1/provider/(?P<provider_id>\d+)/occupancy/$',
        Occupancy.as_view()),
    url(r'^api/v1/provider/(?P<provider_id>\d+)/hypervisor/$',
        Hypervisor.as_view()),

    url(r'^api/v1/group/$', GroupList.as_view()),
    url(r'^api/v1/group/(?P<groupname>.*)/$', Group.as_view()),

    url(r'^api/v1/tag/$', TagList.as_view()),
    url(r'^api/v1/tag/(?P<tag_slug>.*)/$', Tag.as_view()),

    url(r'^api/v1/application/$',
        ApplicationListNoAuth.as_view(),
        name='application-list-no-auth'),

    url(r'^api/v1/instance/$', InstanceHistory.as_view(),
        name='instance-history'),

    url(r'^api/v1/request_image/$',
        MachineRequestStaffList.as_view(), name='direct-machine-request-list'),
    url(r'^api/v1/request_image/(?P<machine_request_id>\d+)/$',
        MachineRequestStaff.as_view(), name='direct-machine-request-detail'),
    url(r'^api/v1/request_image/(?P<machine_request_id>\d+)/(?P<action>.*)/$',
        MachineRequestStaff.as_view(), name='direct-machine-request-action'),


    url(r'^api/v1/provider/(?P<provider_id>\d+)/account/(?P<username>\w+)/$',
        Account.as_view(), name='account-management'),


    url(r'^api/v1/provider/(?P<provider_id>\d+)'
        + '/identity/(?P<identity_id>\d+)/image_export/$',
        MachineExportList.as_view(), name='machine-export-list'),
    url(r'^api/v1/provider/(?P<provider_id>\d+)'
        + '/identity/(?P<identity_id>\d+)/image_export/(?P<machine_request_id>\d+)/$',
        MachineExport.as_view(), name='machine-export'),


    url(r'^api/v1/provider/(?P<provider_id>\d+)'
    + '/identity/(?P<identity_id>\d+)/request_image/$',
        MachineRequestList.as_view(), name='machine-request-list'),
    url(r'^api/v1/provider/(?P<provider_id>\d+)'
    + '/identity/(?P<identity_id>\d+)/request_image/(?P<machine_request_id>\d+)/$',
        MachineRequest.as_view(), name='machine-request'),


    url(r'^api/v1/provider/(?P<provider_id>\d+)'
    + '/identity/(?P<identity_id>\d+)/profile/$',
        Profile.as_view(), name='profile-detail'),


    url(r'^api/v1/provider/(?P<provider_id>\d+)'
        + '/identity/(?P<identity_id>\d+)/instance/'
        + '(?P<instance_id>[a-zA-Z0-9-]+)/action/$',
        InstanceAction.as_view(), name='instance-action'),
    url(r'^api/v1/provider/(?P<provider_id>\d+)'
        + '/identity/(?P<identity_id>\d+)/instance/history/$',
        InstanceHistory.as_view(), name='instance-history'),
    url(r'^api/v1/provider/(?P<provider_id>\d+)'
        + '/identity/(?P<identity_id>\d+)/instance/(?P<instance_id>[a-zA-Z0-9-]+)/$',
        Instance.as_view(), name='instance-detail'),
    url(r'^api/v1/provider/(?P<provider_id>\d+)'
        + '/identity/(?P<identity_id>\d+)/instance/$',
        InstanceList.as_view(), name='instance-list'),


    url(r'^api/v1/provider/(?P<provider_id>\d+)'
        + '/identity/(?P<identity_id>\d+)/size/$',
        SizeList.as_view(), name='size-list'),
    url(r'^api/v1/provider/(?P<provider_id>\d+)'
        + '/identity/(?P<identity_id>\d+)/size/(?P<size_id>\d+)/$',
        Size.as_view(), name='size-detail'),


    url(r'^api/v1/provider/(?P<provider_id>\d+)'
        + '/identity/(?P<identity_id>\d+)/step/$',
        StepList.as_view(), name='step-list'),
    url(r'^api/v1/provider/(?P<provider_id>\d+)'
        + '/identity/(?P<identity_id>\d+)/step/(?P<step_id>[a-zA-Z0-9-]+)/$',
        Step.as_view(), name='step-detail'),


    url(r'^api/v1/provider/(?P<provider_id>\d+)'
        + '/identity/(?P<identity_id>\d+)/volume/$',
        VolumeList.as_view(), name='volume-list'),
    url(r'^api/v1/provider/(?P<provider_id>\d+)'
        + '/identity/(?P<identity_id>\d+)/volume/(?P<volume_id>[a-zA-Z0-9-]+)/$',
        Volume.as_view(), name='volume-detail'),


    url(r'^api/v1/provider/(?P<provider_id>\d+)'
        + '/identity/(?P<identity_id>\d+)/machine/$',
        MachineList.as_view(), name='machine-list'),
    url(r'^api/v1/provider/(?P<provider_id>\d+)'
        + '/identity/(?P<identity_id>\d+)/machine/history/$',
        MachineHistory.as_view(), name='machine-history'),
    url(r'^api/v1/provider/(?P<provider_id>\d+)'
        + '/identity/(?P<identity_id>\d+)/machine/search/$',
        MachineSearch.as_view(), name='machine-search'),
    url(r'^api/v1/provider/(?P<provider_id>\d+)'
        + '/identity/(?P<identity_id>\d+)/machine/(?P<machine_id>[a-zA-Z0-9-]+)/$',
        Machine.as_view(), name='machine-detail'),


    url(r'^api/v1/provider/(?P<provider_id>\d+)'
        + '/identity/(?P<identity_id>\d+)/meta/$', Meta.as_view(), name='meta-detail'),
    url(r'^api/v1/provider/(?P<provider_id>\d+)'
        + '/identity/(?P<identity_id>\d+)/meta/(?P<action>.*)/$',
        MetaAction.as_view(), name='meta-action'),


    url(r'^api/v1/provider/(?P<provider_id>\d+)'
        + '/identity/(?P<identity_id>\d+)/$',
        IdentityMembershipList.as_view(), name='identity-membership-list'),
    url(r'^api/v1/provider/(?P<provider_id>\d+)'
        + '/identity/(?P<identity_id>\d+)/$',
        IdentityMembership.as_view(), name='identity-membership-detail'),
    url(r'^api/v1/provider/(?P<provider_id>\d+)'
        + '/identity/$', IdentityList.as_view(), name='identity-list'),
    url(r'^api/v1/provider/(?P<provider_id>\d+)'
        + '/identity/(?P<identity_id>\d+)/$',
        Identity.as_view(), name='identity-detail'),

    url(r'^api/v1/identity/$', IdentityDetailList.as_view(),
        name='identity-detail-list'),

    url(r'^api/v1/provider/$', ProviderList.as_view(), name='provider-list'),
    url(r'^api/v1/provider/(?P<provider_id>\d+)/$',
        Provider.as_view(), name='provider-detail'),

))

urlpatterns += staticfiles_urlpatterns()
