from django.utils.timezone import datetime, timedelta

import jwt
import requests

from caslib import OAuthClient
from threepio import auth_logger as logger

from atmosphere.settings import secrets
from atmosphere import settings
from authentication import get_or_create_user
from authentication.models import Token as AuthToken
from core.models.user import AtmosphereUser





# Requests auth class for access tokens
class TokenAuth(requests.auth.AuthBase):

    """
    Authentication using the protocol:
    Token <access_token>
    """

    def __init__(self, access_token):
        self.access_token = access_token

    def __call__(self, r):
        r.headers['Authorization'] = "Token %s" % self.access_token
        return r


############################
# METHODS SPECIFIC TO GROUPY!
############################
def create_user(username):
    oauth_attrs = lookupUser(username)
    attributes = oauth_formatAttrs(oauth_attrs)
    # FIXME: valid user should actually be set
    valid_user = None
    user = get_or_create_user(valid_user, attributes)
    return user


def get_token_for_user(username):
    access_token, _ = generate_access_token(
        open(secrets.OAUTH_PRIVATE_KEY).read(),
        iss=secrets.OAUTH_ISSUE_USER,
        sub=username,
        scope=secrets.OAUTH_SCOPE)
    # TODO: TokenAuth here
    response = requests.get(
        '%s/o/oauth2/tokeninfo?access_token=%s'
        % (secrets.GROUPY_SERVER, access_token),
        headers={'Authorization': 'Token %s' % access_token})
    json_obj = response.json()
    if 'on_behalf' in json_obj:
        username = json_obj['on_behalf']
        expires = datetime.now() + timedelta(seconds=json_obj['expires_in'])
        return username, expires
    return None, None


def get_user_for_token(test_token):
    access_token, _ = generate_access_token(
        open(secrets.OAUTH_PRIVATE_KEY).read(),
        iss=secrets.OAUTH_ISSUE_USER,
        scope=secrets.OAUTH_SCOPE)
    # TODO: TokenAuth here
    response = requests.get(
        '%s/o/oauth2/tokeninfo?access_token=%s'
        % (secrets.GROUPY_SERVER, test_token),
        headers={'Authorization': 'Token %s' % access_token})
    json_obj = response.json()
    logger.debug(json_obj)
    if 'on_behalf' in json_obj:
        username = json_obj['on_behalf']
        expires = datetime.now() + timedelta(seconds=json_obj['expires_in'])
        return username, expires
    return None, None


def get_atmo_users():
    access_token, _ = generate_access_token(
        open(secrets.OAUTH_PRIVATE_KEY).read(),
        iss=secrets.OAUTH_ISSUE_USER,
        scope=secrets.OAUTH_SCOPE)
    response = requests.get(
        '%s/api/groups/atmo-user/members'
        % secrets.GROUPY_SERVER,
        headers={'Authorization': 'Token %s' % access_token})
    return response


def lookupUser(username):
    access_token, _ = generate_access_token(
        open(secrets.OAUTH_PRIVATE_KEY).read(),
        iss=secrets.OAUTH_ISSUE_USER,
        scope=secrets.OAUTH_SCOPE)
    response = requests.get('%s/api/users/%s'
                            % (secrets.GROUPY_SERVER,
                                username))
    user_data = response.json()
    return user_data


def oauth_formatAttrs(oauth_attrs):
    """
    Formats attrs into a unified dict to ease in user creation
    """
    try:
        return {
            'email': oauth_attrs['mail'],
            'firstName': oauth_attrs['givenname'],
            'lastName': oauth_attrs['sn'],
        }
    except KeyError as nokey:
        logger.exception(nokey)
        return None


def get_staff_users():
    access_token, _ = generate_access_token(
        open(secrets.OAUTH_PRIVATE_KEY).read(),
        iss=secrets.OAUTH_ISSUE_USER,
        scope=secrets.OAUTH_SCOPE)
    response = requests.get('%s/api/groups/staff/members'
                            % secrets.GROUPY_SERVER)
    staff_users = [user['name'] for user in response.json()['data']]
    return staff_users


def get_core_services():
    access_token, _ = generate_access_token(
        open(secrets.OAUTH_PRIVATE_KEY).read(),
        iss=secrets.OAUTH_ISSUE_USER,
        scope=secrets.OAUTH_SCOPE)
    response = requests.get('%s/api/groups/core-services/members'
                            % secrets.GROUPY_SERVER)
    cs_users = [user['name'] for user in response.json()['data']]
    return cs_users


def is_atmo_user(username):
    access_token, _ = generate_access_token(
        open(secrets.OAUTH_PRIVATE_KEY).read(),
        iss=secrets.OAUTH_ISSUE_USER,
        scope=secrets.OAUTH_SCOPE)
    response = requests.get('%s/api/groups/atmo-user/members'
                            % secrets.GROUPY_SERVER)
    atmo_users = [user['name'] for user in response.json()['data']]
    return username in atmo_users


def generate_access_token(pem_id_key, iss='atmosphere',
                          scope='groups search', sub=None):
    if not pem_id_key:
        raise Exception("Private key missing. "
                        "Key is required for JWT signature")
    # 1. Create and encode JWT (using our pem key)
    kwargs = {'iss': iss,
              'scope': scope}
    if sub:
        kwargs['sub'] = sub
    jwt_object = jwt.create(**kwargs)
    encoded_sig = jwt.encode(jwt_object, pem_id_key)

    # 2. Pass JWT to gables and return access_token
    # If theres a 'redirect_uri' then redirect the user
    response = requests\
        .post("%s/o/oauth2/token" % secrets.GROUPY_SERVER,
              data={
                  'assertion': encoded_sig,
                  'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer'
              })
    if response.status_code != 200:
        raise Exception("Failed to generate auth token. Response:%s"
                        % response.__dict__)
    json_obj = response.json()
    access_token, expires_in = json_obj['access_token'], json_obj['expires_in']
    expires = datetime.utcnow() + timedelta(seconds=expires_in)
    return access_token, expires


def read_access_token(access_token):
    payload = {'access_token': access_token}
    response = requests.get("%s/o/oauth2/tokeninfo" % secrets.GROUPY_SERVER,
                            params=payload)
    if response.status_code != 200:
        raise Exception("Failed to read auth token. Response:%s" % response)
    return response.text


def generate_keys():
    """
    Note: This doesnt work.
    """
    response = requests.post("%s/apps/groupy/keys" % secrets.GROUPY_SERVER)
    if response.status_code != 200:
        raise Exception("Failed to generate auth token. Response:%s"
                        % response)
    json_obj = response.json()
    pem_id_key = json_obj['private']
    return pem_id_key


###########################
# CAS-SPECIFIC OAUTH METHODS
###########################
def get_cas_oauth_client():
    o_client = OAuthClient(settings.CAS_SERVER,
                           settings.OAUTH_CLIENT_CALLBACK,
                           settings.OAUTH_CLIENT_KEY,
                           settings.OAUTH_CLIENT_SECRET,
                           auth_prefix=settings.CAS_AUTH_PREFIX)
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
