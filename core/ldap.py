"""
Basic LDAP functions.
"""
from __future__ import absolute_import

import ldap as ldap_driver

from atmosphere.logger import logger
from atmosphere import settings


def get_uid_number(userid):
    """
    Get uidNumber
    """
    try:
        conn = ldap_driver.initialize(settings.LDAP_SERVER)
        attr = conn.search_s(settings.LDAP_SERVER_DN,
                             ldap_driver.SCOPE_SUBTREE,
                             "(uid=%s)" % userid)
        return int(attr[0][1]["uidNumber"][0]) - 10000
    except Exception as e:
        logger.warn("Error occurred getting user uidNumber for user: %s" % userid)
        logger.exception(e)
        return None
