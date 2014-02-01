"""
LDAP authentication methods
"""
from __future__ import absolute_import
import string

from django.core.handlers.wsgi import WSGIRequest

import ldap as ldap_driver

from threepio import logger

from atmosphere.settings import secrets


def _search_ldap(userid, conn=None):
    try:
        if not conn:
            conn = ldap_driver.initialize(secrets.LDAP_SERVER)
        result = conn.search_s(
            secrets.LDAP_SERVER_DN,
            ldap_driver.SCOPE_SUBTREE,
            '(uid='+userid+')'
        )
        return result
    except Exception as e:
        logger.warn("Error occurred on ldap search for: %s" % userid)
        logger.exception(e)
        return None


def getAllUsers():
    """
    Grabs all users in LDAP
    """
    try:
        conn = ldap_driver.initialize(secrets.LDAP_SERVER)
        user_list = []
        for letter in string.lowercase:
            attr = _search_ldap("%s*" % letter, conn)
            for i in xrange(0, len(attr)):
                user_attrs = attr[i][1]
                user_list.append(user_attrs)
        return user_list
    except Exception as e:
        logger.warn("Error occurred looking up user: %s" % userid)
        logger.exception(e)
        return None


def lookupUser(userid):
    """
    Grabs email for the user based on LDAP attrs
    """
    try:
        attr = _search_ldap(userid)
        user_attrs = attr[0][1]
        return user_attrs
    except Exception as e:
        logger.warn("Error occurred looking up user: %s" % userid)
        logger.exception(e)
        return None


def lookupEmail(userid):
    """
    Grabs email for the user based on LDAP attrs
    """
    try:
        logger.debug(type(userid))
        if isinstance(userid, WSGIRequest):
            raise Exception("WSGIRequest invalid.")
        attr = _search_ldap(userid)
        emailaddr = attr[0][1]['mail'][0]
        return emailaddr
    except Exception as e:
        logger.warn("Error occurred looking up email for user: %s" % userid)
        logger.exception(e)
        import traceback
        import sys
        import inspect
        s = inspect.stack()
        for i in range(0, 4):
            logger.debug(s[i])
        etype, value, tb = sys.exc_info()
        logger.error("TB = %s" % traceback.format_tb(tb))

        return None


def ldap_validate(username, password):
    """
    ldap_validate
    Using the username and password parameters, test with an LDAP bind.
    If the connection succeeds, the credentials are authentic.
    """
    try:
        ldap_server = secrets.LDAP_SERVER
        ldap_server_dn = secrets.LDAP_SERVER_DN
        logger.warn("[LDAP] Validation Test - %s" % username)
        ldap_conn = ldap_driver.initialize(ldap_server)
        dn = "uid="+username+","+ldap_server_dn
        ldap_conn.simple_bind_s(dn, password)
        return True
    except Exception as e:
        logger.exception(e)
        return False


def ldap_formatAttrs(ldap_attrs):
    """
    Formats attrs into a unified dict to ease in user creation
    """
    logger.info(ldap_attrs)
    try:
        return {
            'email': ldap_attrs['mail'][0],
            'firstName': ldap_attrs['givenName'][0],
            'lastName': ldap_attrs['sn'][0],
        }
    except KeyError as nokey:
        logger.exception(nokey)
        return None


def is_atmo_user(username):
    """
    ldap_validate
    Using the username is in the atmo-user group return True
    otherwise False.
    """
    try:
        ldap_server = secrets.LDAP_SERVER
        ldap_group_dn = secrets.LDAP_SERVER_DN.replace(
            "ou=people", "ou=Groups")
        ldap_conn = ldap_driver.initialize(ldap_server)
        atmo_users = ldap_conn.search_s(ldap_group_dn,
                                        ldap_driver.SCOPE_SUBTREE,
                                        '(cn=atmo-user)')
        return username in atmo_users[0][1]['memberUid']
    except Exception as e:
        logger.exception(e)
        return False


def get_core_services():
    """
    """
    try:
        ldap_server = secrets.LDAP_SERVER
        ldap_group_dn = secrets.LDAP_SERVER_DN.replace(
            "ou=people", "ou=Groups")
        ldap_conn = ldap_driver.initialize(ldap_server)
        atmo_users = ldap_conn.search_s(ldap_group_dn,
                                        ldap_driver.SCOPE_SUBTREE,
                                        '(cn=core-services)')
        return atmo_users[0][1]['memberUid']
    except Exception as e:
        logger.exception(e)
        return False

def get_staff_users():
    """
    """
    try:
        ldap_server = secrets.LDAP_SERVER
        ldap_group_dn = secrets.LDAP_SERVER_DN.replace(
            "ou=people", "ou=Groups")
        ldap_conn = ldap_driver.initialize(ldap_server)
        atmo_users = ldap_conn.search_s(ldap_group_dn,
                                        ldap_driver.SCOPE_SUBTREE,
                                        '(cn=staff)')
        return atmo_users[0][1]['memberUid']
    except Exception as e:
        logger.exception(e)
        return False

