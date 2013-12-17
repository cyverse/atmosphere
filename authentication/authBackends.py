"""
Authentication Backends and validation methods

"""
from django.contrib.auth.backends import ModelBackend
from core.models import AtmosphereUser as DjangoUser

from threepio import logger

from authentication.protocol.ldap import ldap_validate, ldap_formatAttrs, lookupUser
from authentication.protocol.cas import cas_validateUser, cas_formatAttrs


def makeOrCreateUser(username=None, attributes=None):
    """
    Retrieve or create a DjangoUser matching the username (No password)
    """
    if not username:
        return None
    try:
        user = DjangoUser.objects.get(username=username)
    except DjangoUser.DoesNotExist:
        user = DjangoUser.objects.create_user(username, "")
    if attributes:
        user.first_name = attributes['firstName']
        user.last_name = attributes['lastName']
        user.email = attributes['email']
    user.save()
    return user


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
        (success, cas_response) = cas_validateUser(username)
        if not success:
            logger.debug("CAS Authentication failed - "+username)
            return None
        attributes = cas_formatAttrs(cas_response)
        return makeOrCreateUser(username, attributes)


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
        ldap_attrs = lookupUser(username)
        attributes = ldap_formatAttrs(ldap_attrs)
        return makeOrCreateUser(username, attributes)
