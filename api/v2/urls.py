# -*- coding: utf-8 -*-
"""
Routes for api v2 endpoints
"""
from django.conf.urls import include, url
from rest_framework import routers
from api.v2 import views
from api.base import views as base_views

router = routers.DefaultRouter(trailing_slash=False)
router.register(r'accounts', views.AccountViewSet, base_name='account')
router.register(
    r'allocations',
    views.AllocationViewSet,
    base_name='allocation')
router.register(r'allocation_sources', views.AllocationSourceViewSet)
router.register(r'boot_scripts', views.BootScriptViewSet)
router.register(r'credentials', views.CredentialViewSet)
router.register(r'events', views.EventViewSet, base_name='event')
router.register(r'email_template', views.EmailTemplateViewSet)
router.register(r'email_feedback', views.FeedbackEmailViewSet, base_name='email-feedback')
router.register(r'email_instance_report', views.InstanceSupportEmailViewSet, base_name='instance-email-support')
router.register(r'email_volume_report', views.VolumeSupportEmailViewSet, base_name='volume-email-support')
router.register(r'email_request_resources', views.ResourceEmailViewSet, base_name='email-request-resources')
router.register(r'emulate_token', views.TokenEmulateViewSet, base_name='emulate-token')
router.register(r'emulate_session', views.SessionEmulateViewSet, base_name='emulate-session')
router.register(r'help_links', views.HelpLinkViewSet)
router.register(r'identities', views.IdentityViewSet)
router.register(r'identity_memberships', views.IdentityMembershipViewSet, base_name='identitymembership')
router.register(r'images', views.ImageViewSet, base_name='application')
router.register(r'image_bookmarks', views.ImageBookmarkViewSet)
router.register(r'image_tags', views.ImageTagViewSet)
router.register(
    r'image_versions',
    views.ImageVersionViewSet,
    base_name='imageversion')
router.register(
    r'image_version_licenses',
    views.ImageVersionLicenseViewSet,
    base_name='imageversion_license')
router.register(
    r'image_version_memberships',
    views.ImageVersionMembershipViewSet,
    base_name='imageversion_membership')
router.register(
    r'image_version_boot_scripts',
    views.ImageVersionBootScriptViewSet,
    base_name='imageversion_bootscript')
router.register(r'instances', views.InstanceViewSet, base_name='instance')
router.register(r'instance_actions',
    views.InstanceActionViewSet,
    base_name='instanceaction')
router.register(r'instance_histories',
    views.InstanceStatusHistoryViewSet,
    base_name='instancestatushistory')
router.register(r'instance_tags', views.InstanceTagViewSet)
router.register(r'licenses', views.LicenseViewSet)
router.register(r'links', views.ExternalLinkViewSet)
router.register(r'machine_requests', views.MachineRequestViewSet)
router.register(r'maintenance_records', views.MaintenanceRecordViewSet)
router.register(r'metrics', views.MetricViewSet)
router.register(r'platform_types', views.PlatformTypeViewSet)
router.register(r'projects', views.ProjectViewSet)
router.register(r'project_links', views.ProjectExternalLinkViewSet, base_name='projectlinks')
router.register(r'project_images', views.ProjectApplicationViewSet)
router.register(r'project_instances', views.ProjectInstanceViewSet)
router.register(r'project_volumes', views.ProjectVolumeViewSet)
router.register(r'providers', views.ProviderViewSet)
router.register(
    r'provider_machines',
    views.ProviderMachineViewSet,
    base_name='providermachine')
router.register(r'provider_types', views.ProviderTypeViewSet, base_name='providertype')
router.register(r'quotas', views.QuotaViewSet)
router.register(r'resource_requests', views.ResourceRequestViewSet)
router.register(r'reporting', views.ReportingViewSet, base_name='reporting')
router.register(r'sizes', views.SizeViewSet)
router.register(r'status_types', views.StatusTypeViewSet)
router.register(r'tags', views.TagViewSet)
router.register(r'tokens', views.TokenViewSet, base_name='token')
router.register(r'users', views.UserViewSet)
router.register(r'groups', views.GroupViewSet, base_name='group')
router.register(r'volumes', views.VolumeViewSet, base_name='volume')
router.register(r'ssh_keys', views.SSHKeyViewSet, base_name='ssh_key')
router.register(r'version', base_views.VersionViewSet,
                base_name='version-atmo')
router.register(r'deploy_version', base_views.DeployVersionViewSet,
                base_name='version-deploy')

api_v2_urls = router.urls
urlpatterns = [url(r'^', include(api_v2_urls))]
