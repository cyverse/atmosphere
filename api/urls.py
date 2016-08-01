# -*- coding: utf-8 -*-
"""
Top level routes for the api endpoints
"""
from django.conf.urls import url, include
from api.v2 import urls as v2_urls
from api.v1 import urls as v1_urls
from api.status import urls as status_urls
#from api import v1, v2, status

urlpatterns = [
    url(r'', include(v2_urls, namespace="default")),
    url(r'^v1/', include(v1_urls, namespace="v1")),
    url(r'^v2/', include(v2_urls, namespace="v2")),
    url(r'^status/', include(status_urls, namespace="status"))
]
