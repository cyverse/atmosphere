"""
   Logic related to License, PatternMatch, etc. for atmosphere.
"""

from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

from threepio import logger


def _test_license(license, identity):
    """
    If license has an access_list, verify that the identity passes the pattern_match.
    """
    if not license.access_list.count():
        return True
    for pattern_match in license.access_list.iterator():
        result = pattern_match.validate(identity.created_by)
        if result:
            return True
    return False


def is_url(test_string):
    val = URLValidator()
    try:
        val(test_string)
        return True
    except ValidationError:
        return False
    except:
        logger.exception("URL Validation no longer works -- Code fix required")
        return False
