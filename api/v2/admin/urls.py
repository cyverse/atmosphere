from django.conf.urls import include, url
from rest_framework import routers
from api.v2 import views

router = routers.DefaultRouter(trailing_slash=False)
router.register(r'resource_requests', views.AdminResourceRequestViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
]
