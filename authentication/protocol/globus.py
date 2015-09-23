import requests

from base64 import b64encode
from django.http import HttpResponse, HttpResponseRedirect
from django.utils import timezone

from oauth2client.client import OAuth2WebServerFlow
from oauth2client.client import Error as OAuthError

from authentication.models import create_token, create_access_token, get_access_token
from authentication.settings import auth_settings

import logging
logger = logging.getLogger(__name__)

def globus_bootstrap():
    """
    'BootStrap' OAuth by passing the identifying services:
    ClientID && ClientSecret w/ 'client_credentials' Grant & Scope
    """
    data = {
        'grant_type': 'client_credentials',
        'scope': auth_settings.GLOBUS_OAUTH_CREDENTIALS_SCOPE
    }
    userAndPass = "%s:%s" % (auth_settings.GLOBUS_OAUTH_ID, auth_settings.GLOBUS_OAUTH_SECRET)
    b64enc_creds = b64encode(userAndPass)
    response = requests.post(
            auth_settings.GLOBUS_TOKEN_URL,
            data=data,
            headers={
                'Authorization': 'Basic %s' % b64enc_creds,
                'content-type': 'x-www-form-urlencoded'})
    if response.status_code != 200:
        raise Exception("Received unexpected result from OAuth Server. Check Response:%s" % response.__dict__)
    json_obj = response.json()
    return json_obj

def globus_initFlow():
    """
    Retrieve cached/Create a new access token
    and use it to create an OAuth2WebServerFlow
    """
    access_token = get_access_token(auth_settings.GLOBUS_TOKEN_URL)
    if not access_token:
        #Cache it.
        start_time = timezone.now()
        globus_token = globus_bootstrap()
        token_expiry = start_time + timezone.timedelta(seconds=globus_token['expires_in'])
        token_key = globus_token['access_token']
        access_token = create_access_token(
                token_key, token_expiry,
                auth_settings.GLOBUS_TOKEN_URL)
    # use access_token as a Bearer Token
    flow = OAuth2WebServerFlow(
        client_id=auth_settings.GLOBUS_OAUTH_ID,
        scope=auth_settings.GLOBUS_OAUTH_AUTHENTICATION_SCOPE,
        authorization_header="Bearer %s" % access_token.key,
        redirect_uri=auth_settings.OAUTH_CLIENT_CALLBACK,
        auth_uri=auth_settings.GLOBUS_AUTH_URL,
        token_uri=auth_settings.GLOBUS_TOKEN_URL)
    return flow


def globus_authorize(request):
    """
    Redirect to the IdP based on 'flow'
    """
    flow = globus_initFlow()
    auth_uri = flow.step1_get_authorize_url()
    return HttpResponseRedirect(auth_uri)

def _extract_username_from_email(user_email):
    """
    Input:  test@fake.com
    Output: test
    """
    return user_email.split('@')[0]


def globus_validate_code(request):
    """
    Validate 'code' returned from the IdP
    If valid: Return new AuthToken
        else: Return None
    """
    code = request.GET['code']
    if not code:
        return HttpResponse("NO Code found!")
    if type(code) == list:
        code = code[0]
    flow = globus_initFlow()
    try:
        credentials = flow.step2_exchange(code)
    except OAuthError as err:
        logger.exception("Error exchanging code w/ globus")
        return None
    token_profile = credentials.id_token
    username = token_profile['username']
    username = _extract_username_from_email(username)
    email = token_profile['username']
    full_name = token_profile['name']
    issuer = token_profile['iss']
    access_token = credentials.access_token
    expiry_date = credentials.token_expiry
    auth_token = create_token(username, access_token, expiry_date, issuer)
    return auth_token
