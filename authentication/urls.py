# -*- coding: utf-8 -*-
"""
Routes for authentication services
"""
from django.conf.urls import patterns, url


urlpatterns = patterns(
    '',
    url(r'^s_serviceValidater$',
        'authentication.protocol.cas.saml_validateTicket',
        name="saml-service-validate-link"),

    # CAS Authentication Section:
    #    CAS Validation:
    #    Service URL validates the ticket returned after CAS login
    url(r'^CAS_serviceValidater',
        'authentication.protocol.cas.cas_validateTicket',
        name='cas-service-validate-link'),

    # A valid callback URL for maintaining proxy requests
    # This URL retrieves Proxy IOU combination
    url(r'^CAS_proxyCallback',
        'authentication.protocol.cas.cas_proxyCallback',
        name='cas-proxy-callback-link'),
    # This URL retrieves maps Proxy IOU & ID
    url(r'^CAS_proxyUrl',
        'authentication.protocol.cas.cas_storeProxyIOU_ID',
        name='cas-proxy-url-link'),
    url(r'^CASlogin/(?P<redirect>.*)$', 'authentication.cas_loginRedirect'))
