# -*- coding: utf-8 -*-
"""
Routes for authentication services
"""
from django.conf.urls import patterns, url


urlpatterns = patterns(
    '',
    url(r'^o_login$', 'authentication.views.o_login_redirect'),
    # OAuth Authentication Section:
    url(r'^oauth2.0/callbackAuthorize$', 'authentication.views.o_callback_authorize'),
    # GLOBUS Authentication Section:
    url(r'^globus_login$', 'authentication.views.globus_login_redirect'),

    # CAS Authentication Section:
    #   CAS +OAuth: see 'OAuth Authentication Section'
    #   CAS+SSO:
    url(r'^CASlogin/(?P<redirect>.*)$', 'authentication.protocol.cascas_loginRedirect'),
    url(r'^CAS_serviceValidater',
        'authentication.protocol.cas.cas_validateTicket',
        name='cas-service-validate-link'),
    #   CAS+SSO (+ProxyTicket):
    url(r'^CAS_proxyCallback',
        'authentication.protocol.cas.cas_proxyCallback',
        name='cas-proxy-callback-link'),
    url(r'^CAS_proxyUrl',
        'authentication.protocol.cas.cas_storeProxyIOU_ID',
        name='cas-proxy-url-link'),
    # CAS + SAML Validation
    url(r'^s_serviceValidater$',
        'authentication.protocol.cas.saml_validateTicket',
        name="saml-service-validate-link")
)
