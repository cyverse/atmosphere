import requests

from base64 import b64encode
from django.http import HttpResponse, HttpResponseRedirect
from oauth2client.client import OAuth2WebServerFlow

from authentication.models import create_token

from atmosphere.settings import OAUTH_CLIENT_CALLBACK
from atmosphere.settings.secrets import GLOBUS_OAUTH_ID, GLOBUS_OAUTH_SECRET, GLOBUS_OAUTH_AUTHENTICATION_SCOPE, GLOBUS_OAUTH_CREDENTIALS_SCOPE, GLOBUS_TOKEN_URL, GLOBUS_AUTH_URL


def globus_bootstrap():
    """
    'BootStrap' OAuth by passing the identifying services:
    ClientID && ClientSecret w/ 'client_credentials' Grant & Scope
    """
    data = {
        'grant_type': 'client_credentials',
        'scope': GLOBUS_OAUTH_CREDENTIALS_SCOPE
    }
    userAndPass = "%s:%s" % (GLOBUS_OAUTH_ID, GLOBUS_OAUTH_SECRET)
    b64enc_creds = b64encode(userAndPass)
    response = requests.post(
            GLOBUS_TOKEN_URL,
            data=data,
            headers={
                'Authorization': 'Basic %s' % b64enc_creds,
                'content-type': 'x-www-form-urlencoded'})
    if response.status_code == 200:
        json_obj = response.json()
    return json_obj['access_token']

def globus_initFlow():
    oauth_token = globus_bootstrap()
    flow = OAuth2WebServerFlow(
        client_id=GLOBUS_OAUTH_ID,
        scope=GLOBUS_OAUTH_AUTHENTICATION_SCOPE,
        authorization_header="Bearer %s" % oauth_token,
        redirect_uri=OAUTH_CLIENT_CALLBACK,
        auth_uri=GLOBUS_AUTH_URL,
        token_uri=GLOBUS_TOKEN_URL)
    return flow


def globus_authorize(request):
    """
    Redirect to the IdP based on 'flow'
    """
    flow = globus_initFlow()
    redirect_to = request.GET.get('redirect_url', '/application')
    request.session['redirect_to'] = redirect_to
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
    Redirect from the Idp to the intended area
    """
    code = request.GET['code']
    if not code:
        return HttpResponse("NO Code found!")
    if type(code) == list:
        code = code[0]
    flow = globus_initFlow()
    credentials = flow.step2_exchange(code)
    token_profile = credentials.id_token
    username = token_profile['username']
    username = _extract_username_from_email(username)
    email = token_profile['username']
    full_name = token_profile['name']
    issuer = token_profile['iss']
    access_token = credentials.access_token
    expiry_date = credentials.token_expiry
    auth_token = create_token(username, access_token, expiry_date, issuer)
    request.session['username'] = username
    request.session['token'] = auth_token.key
    redirect_to = request.session.get('redirect_to', '/application')
    return HttpResponseRedirect(redirect_to)
