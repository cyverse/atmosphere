from django.conf.urls import patterns, include, url
from rest_framework import routers
from api.v2 import views

router = routers.DefaultRouter(trailing_slash=False)
router.register(r'tags', views.TagViewSet)
router.register(r'users', views.UserViewSet)
router.register(r'projects', views.ProjectViewSet)
router.register(r'images', views.ImageViewSet)
router.register(r'providers', views.ProviderViewSet)
router.register(r'identities', views.IdentityViewSet)
router.register(r'quotas', views.QuotaViewSet)
router.register(r'allocations', views.AllocationViewSet)
router.register(r'volumes', views.VolumeViewSet)
router.register(r'instances', views.InstanceViewSet)
router.register(r'instance_actions', views.InstanceActionViewSet)
router.register(r'volume_actions', views.VolumeActionViewSet)

urlpatterns = patterns('',
                       url(r'^', include(router.urls)),
                       )
