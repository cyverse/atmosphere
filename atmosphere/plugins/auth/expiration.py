import pytz

from django.utils import timezone
from django_cyverse_auth.protocol.ldap import lookupUser
from threepio import logger


class ExpirationPlugin(object):
    def is_expired(self, user):
        raise NotImplementedError(
            "Validation plugins must implement a validate_user function that "
            "takes a single argument: 'user'")


class AlwaysAllow(ExpirationPlugin):
    def is_expired(self, user):
        return False


class LDAPPasswordExpired(ExpirationPlugin):
    """
    For CyVerse, LDAP Expiration is tested by
    verifying the user 'expiration' date is >= now
    True -- Expired user (Or Lookup error)
    False -- User is not expired.
    """

    def is_expired(self, user):
        ldap_user = lookupUser(user.username)
        if not ldap_user:
            logger.warn("Cannot contact LDAP -- Assume user is expired?")
            return True
        expiry_dict = ldap_user.get('expiry')
        if not expiry_dict:
            logger.error(
                "LDAP password expiration map is missing --"
                " check django_cyverse_auth: %s" % ldap_user)
            return True
        expiry_date = expiry_dict.get('expires_on')
        if not expiry_date:
            logger.error(
                "LDAP password expiration date is missing -- "
                "check django_cyverse_auth: %s" % ldap_user)
            return True
        _is_expired = expiry_date.replace(
            tzinfo=pytz.UTC) < timezone.now()
        return _is_expired
