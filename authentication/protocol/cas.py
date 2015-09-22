"""
CAS authentication protocol

Contact:        Steven Gregory <sgregory@iplantcollaborative.org>
                J. Matt Peterson <jmatt@iplantcollaborative.org>
"""
from datetime import timedelta
import time

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.utils import timezone

from caslib import CASClient, SAMLClient

from threepio import auth_logger as logger

from authentication import create_session_token
from authentication.models import UserProxy
from authentication.settings import auth_settings

###########################
# CAS-SPECIFIC SSO METHODS
###########################


PROXY_TICKET_EXPIRY = timedelta(days=1)
User = get_user_model()


def get_cas_client():
    """
    This is how you initialize a CAS Client
    """
    return CASClient(auth_settings.CAS_SERVER,
                     settings.SERVICE_URL,
                     proxy_url=settings.PROXY_URL,
                     proxy_callback=settings.PROXY_CALLBACK_URL,
                     auth_prefix=auth_settings.CAS_AUTH_PREFIX,
                     self_signed_cert=auth_setting.SELF_SIGNED_CERT)


def cas_logoutRedirect():
    return HttpResponseRedirect(auth_settings.CAS_SERVER +
                                "/cas/logout?service=" + settings.SERVER_URL)


def cas_loginRedirect(request, redirect=None, gateway=False):
    if not redirect:
        redirect = request.get_full_path()
    redirect_to = "%s/CAS_serviceValidater?sendback=%s" \
        % (settings.SERVER_URL, redirect)
    login_url = "%s%s/login?service=%s" \
        % (auth_settings.CAS_SERVER, auth_settings.CAS_AUTH_PREFIX, redirect_to)
    if gateway:
        login_url += '&gateway=true'
    return HttpResponseRedirect(login_url)




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
    except Exception:
        logger.exception('Error validating user %s' % username)
        return (False, None)


def cas_updateUserProxy(user, pgtIou, max_try=3):
    attempts = 0
    while attempts < max_try:
        try:
            # If PGTIOU exists, a UserProxy object was created
            # match the user to this ticket.
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

def cas_set_redirect_url(sendback, request):
    absolute_url = request.build_absolute_uri(
        reverse('authentication:cas-service-validate-link'))
    return "%s?sendback=%s" % (absolute_url, sendback)


def cas_validateTicket(request):
    """
    Method expects 2 GET parameters: 'ticket' & 'sendback'
    After a CAS Login:
    Redirects the request based on the GET param 'ticket'
    Unauthorized Users are redirected to '/' In the event of failure.
    Authorized Users are redirected to the GET param 'sendback'
    """

    redirect_logout_url = settings.REDIRECT_URL + "/login/"
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
    caslib.service_url = cas_set_redirect_url(sendback, request)

    cas_response = caslib.cas_serviceValidate(ticket)
    if not cas_response.success:
        logger.debug("CAS Server did NOT validate ticket:%s"
                     " and included this response:%s (Err:%s)"
                     % (ticket, cas_response.object, cas_response.error_str))
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

    updated = cas_updateUserProxy(
        cas_response.user, cas_response.proxy_granting_ticket)
    if not updated:
        return HttpResponseRedirect(redirect_logout_url)
    logger.info("Updated proxy for <%s> -- Auth success!" % cas_response.user)

    try:
        user = User.objects.get(username=cas_response.user)
    except User.DoesNotExist:
        return HttpResponseRedirect(no_user_url)
    auth_token = create_session_token(None, user, request, issuer="CAS")
    if auth_token is None:
        logger.info("Failed to create AuthToken")
        HttpResponseRedirect(redirect_logout_url)
    return_to = request.GET['sendback']
    logger.info("Session token created, User logged in, return to: %s"
                % return_to)
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


###########################
# CAS-SPECIFIC SAML METHODS
###########################


def get_saml_client():
    s_client = SAMLClient(auth_settings.CAS_SERVER,
                          settings.SERVER_URL,
                          auth_prefix=auth_settings.CAS_AUTH_PREFIX)
    return s_client


def saml_loginRedirect(request, redirect=None, gateway=False):
    login_url = "%s%s/login?service=%s/s_serviceValidater%s" %\
                (auth_settings.CAS_SERVER, auth_settings.CAS_AUTH_PREFIX,
                 settings.SERVER_URL,
                 "?sendback=%s" % redirect if redirect else "")
    if gateway:
        login_url += '&gateway=true'
    return HttpResponseRedirect(login_url)


def saml_validateTicket(request):
    """
    Method expects 2 GET parameters: 'ticket' & 'sendback'
    After a CAS Login:
    Redirects the request based on the GET param 'ticket'
    Unauthorized Users are redirected to '/' In the event of failure.
    Authorized Users are redirected to the GET param 'sendback'
    """

    redirect_logout_url = settings.REDIRECT_URL + "/login/"
    no_user_url = settings.REDIRECT_URL + "/no_user/"
    logger.debug('GET Variables:%s' % request.GET)
    ticket = request.GET.get('ticket', None)

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
        user = User.objects.get(username=saml_response.user)
    except User.DoesNotExist:
        return HttpResponseRedirect(no_user_url)
    auth_token = create_session_token(None, user, request, issuer="CAS+SAML")
    if auth_token is None:
        logger.info("Failed to create AuthToken")
        HttpResponseRedirect(redirect_logout_url)
    return_to = request.GET.get('sendback')
    if not return_to:
        return HttpResponse(saml_response.response,
                            content_type="text/xml; charset=utf-8")
    return_to += "?token=%s" % auth_token
    logger.info("Session token created, return to: %s" % return_to)
    return HttpResponseRedirect(return_to)


###########################
# CAS-SPECIFIC OAUTH METHODS
###########################
def get_cas_oauth_client():
    o_client = OAuthClient(auth_settings.CAS_SERVER,
                           auth_settings.OAUTH_CLIENT_CALLBACK,
                           auth_settings.OAUTH_CLIENT_KEY,
                           auth_settings.OAUTH_CLIENT_SECRET,
                           auth_prefix=auth_settings.CAS_AUTH_PREFIX)
    return o_client


def cas_profile_contains(attrs, test_value):
    # Two basic types of 'values'
    # Lists: e.g. attrs['entitlement'] = ['group1','group2','group3']
    # Objects: e.g. attrs['email'] = 'test@email.com'
    for attr in attrs:
        for (key, value) in attr.items():
            if isinstance(value, list) and test_value in value:
                return True
            elif value == test_value:
                return True
    return False


def cas_profile_for_token(access_token):
    oauth_client = get_cas_oauth_client()
    profile_map = oauth_client.get_profile(access_token)
    return profile_map
