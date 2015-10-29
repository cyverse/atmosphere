# -*- coding: utf-8 -*-
"""
Routes for api v2 endpoints
"""
from django.conf.urls import patterns, include, url
from rest_framework import routers
from api.v2 import views

router = routers.DefaultRouter(trailing_slash=False)
router.register(
    r'allocations',
    views.AllocationViewSet,
    base_name='allocation')
router.register(r'identities', views.IdentityViewSet)
router.register(r'images', views.ImageViewSet, base_name='application')
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
router.register(r'boot_scripts', views.BootScriptViewSet)
router.register(r'credentials', views.CredentialViewSet)
router.register(r'email_support', views.SupportEmailViewSet, base_name='email-support')
router.register(r'email_feedback', views.FeedbackEmailViewSet, base_name='email-feedback')
router.register(r'email_request_resources', views.ResourceEmailViewSet, base_name='email-request-resources')
router.register(r'image_bookmarks', views.ImageBookmarkViewSet)
router.register(r'image_tags', views.ImageTagViewSet)
router.register(r'instances', views.InstanceViewSet, base_name='instance')
router.register(r'instance_histories',
    views.InstanceStatusHistoryViewSet,
    base_name='instancestatushistory')
router.register(r'instance_tags', views.InstanceTagViewSet)
router.register(r'licenses', views.LicenseViewSet)
router.register(r'machine_requests', views.MachineRequestViewSet)
router.register(r'maintenance_records', views.MaintenanceRecordViewSet)
router.register(r'metrics', views.MetricViewSet)
router.register(r'platform_types', views.PlatformTypeViewSet)
router.register(r'projects', views.ProjectViewSet)
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
router.register(r'sizes', views.SizeViewSet)
router.register(r'status_types', views.StatusTypeViewSet)
router.register(r'tags', views.TagViewSet)
router.register(r'users', views.UserViewSet)
router.register(r'groups', views.GroupViewSet, base_name='group')
router.register(r'volumes', views.VolumeViewSet, base_name='volume')

api_v2_urls = router.urls
urlpatterns = patterns('', url(r'^', include(api_v2_urls)),)
