from django.conf.urls import patterns, include, url
from rest_framework import routers
from api.v2 import views

router = routers.DefaultRouter(trailing_slash=False)
router.register(r'image_version', views.ImageVersionViewSet, base_name='imageversion')
router.register(r'allocations', views.AllocationViewSet)
router.register(r'identities', views.IdentityViewSet)
router.register(r'images', views.ImageViewSet, base_name='application')
router.register(r'image_bookmarks', views.ImageBookmarkViewSet)
router.register(r'image_tags', views.ImageTagViewSet)
router.register(r'instances', views.InstanceViewSet)
router.register(r'instance_tags', views.InstanceTagViewSet)
router.register(r'platform_types', views.PlatformTypeViewSet)
router.register(r'projects', views.ProjectViewSet)
router.register(r'project_instances', views.ProjectInstanceViewSet)
router.register(r'project_volumes', views.ProjectVolumeViewSet)
router.register(r'providers', views.ProviderViewSet)
router.register(r'provider_machines', views.ProviderMachineViewSet, base_name='providermachine')
router.register(r'provider_types', views.ProviderTypeViewSet)
router.register(r'quotas', views.QuotaViewSet)
router.register(r'quota_requests', views.QuotaRequestViewSet)
router.register(r'sizes', views.SizeViewSet)
router.register(r'status_types', views.StatusTypeViewSet)
router.register(r'tags', views.TagViewSet)
router.register(r'users', views.UserViewSet)
router.register(r'volumes', views.VolumeViewSet, base_name='volume')

urlpatterns = patterns('',
                       url(r'^', include(router.urls)),
                       )
