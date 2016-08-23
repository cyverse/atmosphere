# -*- coding: utf-8 -*-
"""
Routes for api status endpoints
"""
from django.conf.urls import include, url
from rest_framework import routers

from api.status import views

router = routers.DefaultRouter(trailing_slash=False)
router.register(r'celery', views.CeleryViewSet, base_name='celery')

api_status_urls = router.urls
urlpatterns = [url(r'^', include(api_status_urls)), ]
