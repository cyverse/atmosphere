"""
CAS authentication protocol

Contact:        Steven Gregory <sgregory@iplantcollaborative.org>
                J. Matt Peterson <jmatt@iplantcollaborative.org>

"""
from datetime import timedelta
import time
from django.core.urlresolvers import reverse
from django.utils import timezone
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from core.models import AtmosphereUser as User

from caslib import CASClient, SAMLClient

from threepio import logger

from atmosphere import settings

from authentication import createAuthToken
from authentication.models import UserProxy

from django.core.urlresolvers import reverse

#TODO: Find out the actual proxy ticket expiration time, it varies by server
#May be as short as 5min!
PROXY_TICKET_EXPIRY = timedelta(days=1)

def get_cas_client():
    """
    This is how you initialize a CAS Client
    """
    return CASClient(settings.CAS_SERVER,
            settings.SERVICE_URL,
            proxy_url=settings.PROXY_URL,
            proxy_callback=settings.PROXY_CALLBACK_URL,
            auth_prefix=settings.CAS_AUTH_PREFIX,
            self_signed_cert=settings.SELF_SIGNED_CERT)

def cas_validateUser(username):
    """
    Because this is a programmatic request
    and CAS requires user input when expired,
    We MUST use CAS Proxy Service,
    and see if we can reauthenticate the user.
    """
    try:
        userProxy = UserProxy.objects.filter(username=username).latest('pk')
        logger.debug("[CAS] Validation Test - %s" % username)
        if userProxy is None:
            logger.debug("User %s does not have a proxy" % username)
            return (False, None)
        proxyTicket = userProxy.proxyTicket
        caslib = get_cas_client()
        (validUser, cas_response) =\
            caslib.reauthenticate(proxyTicket, username=username)
        logger.debug("Valid User: %s Proxy response: %s"
                     % (validUser, cas_response))
        return (validUser, cas_response)
    except Exception, e:
        logger.exception('Error validating user %s' % username)
        return (False, None)


def updateUserProxy(user, pgtIou, max_try=3):
    attempts = 0
    while attempts < max_try:
        try:
            #If PGTIOU exists, a UserProxy object was created
            #match the user to this ticket.
            userProxy = UserProxy.objects.get(proxyIOU=pgtIou)
            userProxy.username = user
            userProxy.expiresOn = timezone.now() + PROXY_TICKET_EXPIRY
            logger.debug("Found a matching proxy IOU for %s"
                         % userProxy.username)
            userProxy.save()
            return True
        except UserProxy.DoesNotExist:
            logger.error("Could not find UserProxy object!"
                         "ProxyIOU & ID was not saved "
                         "at proxy url endpoint.")
            time.sleep(min(2**attempts, 8))
            attempts += 1
    return False


def createSessionToken(request, auth_token):
    request.session['username'] = auth_token.user.username
    request.session['token'] = auth_token.key


"""
CAS is an optional way to login to Atmosphere
This code integrates caslib into the Auth system
"""

def _set_redirect_url(sendback, request):
    absolute_url = request.build_absolute_uri(
            reverse('cas-service-validate-link'))
    return "%s?sendback=%s" % (absolute_url, sendback)


def get_saml_client():
    s_client = SAMLClient(settings.CAS_SERVER,
            settings.SERVER_URL,
            auth_prefix=settings.CAS_AUTH_PREFIX)
    return s_client

def saml_validateTicket(request):
    """
    Method expects 2 GET parameters: 'ticket' & 'sendback'
    After a CAS Login:
    Redirects the request based on the GET param 'ticket'
    Unauthorized Users are redirected to '/' In the event of failure.
    Authorized Users are redirected to the GET param 'sendback'
    """

    redirect_logout_url = settings.REDIRECT_URL+"/login/"
    no_user_url = settings.REDIRECT_URL + "/no_user/"
    logger.debug('GET Variables:%s' % request.GET)
    ticket = request.GET.get('ticket', None)
    sendback = request.GET.get('sendback', None)

    if not ticket:
        logger.info("No Ticket received in GET string "
                    "-- Logout user: %s" % redirect_logout_url)
        return HttpResponseRedirect(redirect_logout_url)

    logger.debug("ServiceValidate endpoint includes a ticket."
                 " Ticket must now be validated with SAML")

    # ReturnLocation set, apply on successful authentication

    saml_client = get_saml_client()
    saml_response = saml_client.saml_serviceValidate(ticket)
    if not saml_response.success:
        logger.debug("CAS Server did NOT validate ticket:%s"
                     " and included this response:%s"
                     % (ticket, saml_response.xml))
        return HttpResponseRedirect(redirect_logout_url)

    try:
        auth_token = createAuthToken(saml_response.user)
    except User.DoesNotExist:
        return HttpResponseRedirect(no_user_url)
    if auth_token is None:
        logger.info("Failed to create AuthToken")
        HttpResponseRedirect(redirect_logout_url)
    createSessionToken(request, auth_token)
    return_to = request.GET.get('sendback')
    if not return_to:
        return_to = "%s/application/" % settings.SERVER_URL
    logger.info("Session token created, return to: %s" % return_to)
    return_to += "?token=%s" % auth_token
    return HttpResponseRedirect(return_to)


def cas_validateTicket(request):
    """
    Method expects 2 GET parameters: 'ticket' & 'sendback'
    After a CAS Login:
    Redirects the request based on the GET param 'ticket'
    Unauthorized Users are redirected to '/' In the event of failure.
    Authorized Users are redirected to the GET param 'sendback'
    """

    redirect_logout_url = settings.REDIRECT_URL+"/login/"
    no_user_url = settings.REDIRECT_URL + "/no_user/"
    logger.debug('GET Variables:%s' % request.GET)
    ticket = request.GET.get('ticket', None)
    sendback = request.GET.get('sendback', None)

    if not ticket:
        logger.info("No Ticket received in GET string "
                    "-- Logout user: %s" % redirect_logout_url)
        return HttpResponseRedirect(redirect_logout_url)

    logger.debug("ServiceValidate endpoint includes a ticket."
                 " Ticket must now be validated with CAS")

    # ReturnLocation set, apply on successful authentication

    caslib = get_cas_client()
    caslib.service_url = _set_redirect_url(sendback, request)

    cas_response = caslib.cas_serviceValidate(ticket)
    if not cas_response.success:
        logger.debug("CAS Server did NOT validate ticket:%s"
                     " and included this response:%s"
                     % (ticket, cas_response.object))
        return HttpResponseRedirect(redirect_logout_url)
    if not cas_response.user:
        logger.debug("User attribute missing from cas response!"
                     "This may require a fix to caslib.py")
        return HttpResponseRedirect(redirect_logout_url)
    if not cas_response.proxy_granting_ticket:
        logger.error("""Proxy Granting Ticket missing!
        Atmosphere requires CAS proxy as a service to authenticate users.
            Possible Causes:
              * ServerName variable is wrong in /etc/apache2/apache2.conf
              * Proxy URL does not exist
              * Proxy URL is not a valid RSA-2/VeriSigned SSL certificate
              * /etc/host and hostname do not match machine.""")
        return HttpResponseRedirect(redirect_logout_url)

    updated = updateUserProxy(cas_response.user, cas_response.proxy_granting_ticket)
    if not updated:
        return HttpResponseRedirect(redirect_logout_url)
    logger.info("Updated proxy for <%s> -- Auth success!" % cas_response.user)

    try:
        auth_token = createAuthToken(cas_response.user)
    except User.DoesNotExist:
        return HttpResponseRedirect(no_user_url)
    if auth_token is None:
        logger.info("Failed to create AuthToken")
        HttpResponseRedirect(redirect_logout_url)
    createSessionToken(request, auth_token)
    return_to = request.GET['sendback']
    logger.info("Session token created, return to: %s" % return_to)
    return HttpResponseRedirect(return_to)


"""
CAS as a proxy service is a useful feature to renew
a users token/authentication without having to explicitly redirect the browser.
These two functions will be called
if caslib has been configured for proxy usage. (See #settings.py)
"""


def cas_storeProxyIOU_ID(request):
    """
    Any request to the proxy url will contain the PROXY-TICKET IOU and ID
    IOU and ID are mapped to a DB so they can be used later
    """
    if "pgtIou" in request.GET and "pgtId" in request.GET:
        iou_token = request.GET["pgtIou"]
        proxy_ticket = request.GET["pgtId"]
        logger.debug("PROXY HIT 2 - CAS server sends two IDs: "
                     "1.ProxyIOU (%s) 2. ProxyGrantingTicket (%s)"
                     % (iou_token, proxy_ticket))
        proxy = UserProxy(
            proxyIOU=iou_token,
            proxyTicket=proxy_ticket
        )
        proxy.save()
        logger.debug("Proxy ID has been saved, match ProxyIOU(%s) "
                     "from the proxyIOU returned in service validate."
                     % (proxy.proxyIOU,))
    else:
        logger.debug("Proxy HIT 1 - CAS server tests that this link is HTTPS")

    return HttpResponse("Received proxy request. Thank you.")


def cas_proxyCallback(request):
    """
    This is a placeholder for a proxyCallback service
    needed for CAS authentication
    """
    logger.debug("Incoming request to CASPROXY (Proxy Callback):")
    return HttpResponse("I am at a RSA-2 or VeriSigned SSL Cert. website.")
