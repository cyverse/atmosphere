"""
Authentication Backends and validation methods

"""
from django.contrib.auth.backends import ModelBackend
from core.models import AtmosphereUser as DjangoUser

from threepio import logger

from authentication import get_or_create_user
from authentication.protocol.ldap import ldap_validate, ldap_formatAttrs
from authentication.protocol.ldap import lookupUser as ldap_lookupUser
from authentication.protocol.cas import cas_validateUser, cas_formatAttrs
from authentication.protocol.oauth import get_user_for_token, oauth_formatAttrs
from authentication.protocol.oauth import lookupUser as oauth_lookupUser




class CASLoginBackend(ModelBackend):
    """
    Implemting an AuthenticationBackend
    (Used by Django for logging in to admin, storing session info)
    """
    def authenticate(self, username=None, password=None, request=None):
        """
        Return user if validated by CAS
        Return None otherwise.
        """
        logger.debug("U:%s P:%s R:%s" % (username, password, request))
        if not username:
            logger.debug("CAS Authentication skipped - No Username.")
            return None
        (success, cas_response) = cas_validateUser(username)
        logger.info("Authenticate by CAS: %s - %s %s"
                    % (username, success, cas_response))
        if not success:
            logger.debug("CAS Authentication failed - "+username)
            return None
        attributes = cas_formatAttrs(cas_response)
        return get_or_create_user(username, attributes)


class LDAPLoginBackend(ModelBackend):
    """
    AuthenticationBackend for LDAP logins
    (Logging in from admin or Django REST framework login)
    """
    def authenticate(self, username=None, password=None, request=None):
        """
        Return user if validated by LDAP.
        Return None otherwise.
        """
        if not ldap_validate(username, password):
            logger.debug("LDAP Authentication failed - "+username)
            return None
        ldap_attrs = ldap_lookupUser(username)
        attributes = ldap_formatAttrs(ldap_attrs)
        return get_or_create_user(username, attributes)


class OAuthLoginBackend(ModelBackend):
    """
    AuthenticationBackend for OAuth authorizations
    (Authorize user from Third party (web) clients via OAuth)
    """
    def authenticate(self, username=None, password=None, request=None):
        """
        Return user if validated by LDAP.
        Return None otherwise.
        """
        #First argument, username, should hold the OAuth Token, no password.
        # if 'username' in username, the authentication is meant for CAS
        # if username and password, the authentication is meant for LDAP
        logger.debug("[OAUTH] Authentication Test")
        if not request:
            logger.debug("[OAUTH] Authentication skipped - No Request.")
            return None
        auth = request.META.get('HTTP_AUTHORIZATION', '').split()
        if len(auth) == 2 and auth[0].lower() == "Bearer":
            oauth_token = auth[1]
        logger.debug("[OAUTH] OAuth Token - %s " % oauth_token)

        valid_user, _ = get_user_for_token(oauth_token)
        if not valid_user:
            logger.debug("[OAUTH] Token %s invalid, no user found."
                         % oauth_token)
            return None
        logger.debug("[OAUTH] Authorized user %s" % valid_user)
        oauth_attrs = oauth_lookupUser(valid_user)
        attributes = oauth_formatAttrs(oauth_attrs)
        logger.debug("[OAUTH] Authentication Success - " + valid_user)
        return get_or_create_user(valid_user, attributes)
