"""
CAS authentication protocol

Contact:        Steven Gregory <esteve@iplantcollaborative.org>
                J. Matt Peterson <jmatt@iplantcollaborative.org>

"""
from datetime import datetime, timedelta

from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.contrib.auth.models import User

import caslib

from threepio import logger

from atmosphere import settings

from authentication import createAuthToken
from authentication.models import UserProxy

#TODO: Find out the actual proxy ticket expiration time, it varies by server
#May be as short as 5min!
PROXY_TICKET_EXPIRY = timedelta(days=1)


def cas_validateUser(username):
    """
    Because this is a programmatic request
    and CAS requiers user input when expired,
    We MUST use CAS Proxy Service,
    and see if we can reauthenticate the user.
    """
    try:
        userProxy = UserProxy.objects.filter(username=username).latest('pk')
        logger.debug("[CAS] Validation Test - %s" % username)
        if userProxy is None:
            return (False, None)
        proxyTicket = userProxy.proxyTicket
        (validUser, cas_response) = caslib.cas_reauthenticate(
            username,
            proxyTicket
        )
        return (validUser, cas_response)
    except Exception, e:
        logger.info(str(e))
        return (False, None)


def parse_cas_response(cas_response):
    xml_root_dict = cas_response.map
    #A Success responses will return a dict
    #failed responses will be replaced by an empty dict
    xml_response_dict = xml_root_dict.get(cas_response.type, {})
    user = xml_response_dict.get('user', None)
    pgtIOU = xml_response_dict.get('proxyGrantingTicket', None)
    return (user, pgtIOU)


def updateUserProxy(user, pgtIou):
    try:
        #If PGTIOU exists, a UserProxy object was created
        #match the user to this ticket.
        userProxy = UserProxy.objects.get(proxyIOU=pgtIou)
        userProxy.username = user
        userProxy.expiresOn = datetime.now() + PROXY_TICKET_EXPIRY
        userProxy.save()
        return True
    except UserProxy.DoesNotExist:
        logger.error("Could not find UserProxy object!"
                     + "ProxyIOU & ID was not saved at proxy url endpoint.")
        return False


def createSessionToken(request, auth_token):
    request.session['username'] = auth_token.user.username
    request.session['token'] = auth_token.key
    #TODO: Remove line below
    request.session['api_server'] = settings.API_SERVER_URL


"""
CAS is an optional way to login to Atmosphere
This code integrates caslib into the Auth system
"""


def cas_setReturnLocation(sendback):
    """
    Reinitialize cas with the new sendback location
    keeping all other variables the same.
    """
    caslib.cas_setServiceURL(
        settings.SERVER_URL+"/CAS_serviceValidater?sendback="+sendback
    )


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

    ticket = request.GET.get('ticket', None)
    sendback = request.GET.get('sendback', None)

    if not ticket:
        logger.info("No Ticket -- GoTo %s" % redirect_logout_url)
        return HttpResponseRedirect(redirect_logout_url)

    # ReturnLocation set, apply on successful authentication
    cas_setReturnLocation(sendback)
    cas_response = caslib.cas_serviceValidate(ticket)
    if not cas_response.success:
        #logger.debug("cas_serviceValidate failed")
        return HttpResponseRedirect(redirect_logout_url)
    (user, pgtIou) = parse_cas_response(cas_response)

    if not user:
        logger.debug("User attribute missing from cas response!"
                    + "This may require a fix to caslib.py")
        return HttpResponseRedirect(redirect_logout_url)
    if not pgtIou or pgtIou == "":
        logger.error("""Proxy Granting Ticket missing!
        Atmosphere requires CAS proxy as a service to authenticate users.
            Possible Causes:
              * Proxy URL does not exist
              * Proxy URL is not a valid RSA-2/VeriSigned SSL certificate
              * /etc/host and hostname do not match machine.""")
        return HttpResponseRedirect(redirect_logout_url)

    updated = updateUserProxy(user, pgtIou)
    if not updated:
        return HttpResponseRedirect(redirect_logout_url)

    try:
        auth_token = createAuthToken(user)
    except User.DoesNotExist:
        return HttpResponseRedirect(no_user_url)
    if auth_token is None:
        logger.info("Failed to create AuthToken")
        HttpResponseRedirect(redirect_logout_url)
    createSessionToken(request, auth_token)

    return HttpResponseRedirect(request.GET['sendback'])


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
    logger.info("CASPROXY Call Received:%s" % request.GET)
    if "pgtIou" in request.GET and "pgtId" in request.GET:
        proxy = UserProxy(
            proxyIOU=request.GET["pgtIou"],
            proxyTicket=request.GET["pgtId"]
        )
        proxy.save()
        logger.debug("CASPROXY cas_getProxyID saved IOU,ID:("
                     + proxy.proxyIOU+","+proxy.proxyTicket+")")
    return HttpResponse("Received proxy request. Thank you.")


def cas_proxyCallback(request):
    """
    This is a placeholder for a proxyCallback service
    needed for CAS authentication
    """
    logger.info("Incoming request to CASPROXY (Proxy Callback):")
    return HttpResponse("I am at a RSA-2 or VeriSigned SSL Cert. website.")


def cas_formatAttrs(cas_response):
    """
    Formats attrs into a unified dict to ease in user creation
    """
    try:
        cas_attrs = cas_response.map[cas_response.type]['attributes']
        return cas_attrs
    except KeyError, nokey:
        logger.debug("Error retrieving attributes")
        logger.exception(nokey)
        return None
