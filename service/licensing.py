"""
   Logic related to License, PatternMatch, etc. for atmosphere.
"""

from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

from core.models.license import License, LicenseType
from core.models.match import PatternMatch, MatchType
from core.models.identity import Identity

from threepio import logger


def create_license(title, description, created_by, allow_imaging=True):
    """
    Create a new License, assigning the appropriate LicenseType based on description.
    """
    if is_url(description):
        license_type = LicenseType.objects.get(name="URL")
    else:
        license_type = LicenseType.objects.get(name="Raw Text")
    new_license = License(
        title=title,
        license_type=license_type,
        license_text=description,
        allow_imaging=allow_imaging,
        created_by=created_by)
    new_license.save()
    return new_license


def create_pattern_match(pattern, pattern_type, created_by):
    pattern_type = pattern_type.lower()
    if "email" in pattern_type:
        match_type = MatchType.objects.get(name="BasicEmail")
    elif "user" in pattern_type:
        match_type = MatchType.objects.get(name="Username")
    else:
        raise ValueError("Received invalid pattern_type: %s" % pattern_type)
    pattern = PatternMatch(
        pattern=pattern,
        type=match_type,
        created_by=created_by)
    pattern.save()
    return pattern


def _test_license(license, identity):
    """
    If license has an access_list, verify that the identity passes the test.
    """
    if not license.access_list.count():
        return True
    for test in license.access_list.iterator():
        # TODO: Add more 'type_name' logic here!
        if test.type.name == 'BasicEmail':
            result = _test_user_email(identity.created_by, test.pattern)
        elif test.type.name == "Username":
            result = _test_username(identity.created_by, test.pattern)

        if result:
            return True

    return False


def _simple_match(test_string, pattern, contains=False):
    if contains:
        return pattern in test_string
    else:
        return pattern == test_string


def _simple_glob_test(test_string, pattern):
    from fnmatch import fnmatch
    result = fnmatch(test_string, pattern)
    return result


def _test_user_email(atmo_user, email_pattern):
    email = atmo_user.email.lower()
    email_pattern = email_pattern.pattern.lower()
    result = _simple_glob_test(
        email,
        email_pattern) or _simple_match(
        email,
        email_pattern,
        contains=True)
    logger.info(
        "Email:%s Pattern:%s - Result:%s" %
        (email, email_pattern, result))
    return result


def _test_username(atmo_user, username_match):
    username = atmo_user.username
    result = _simple_match(username, username_match, contains=True)
    logger.info(
        "Username:%s Match On:%s - Result:%s" %
        (username, username_match, result))
    return result


def is_url(test_string):
    val = URLValidator()
    try:
        val(test_string)
        return True
    except ValidationError as e:
        return False
    except:
        logger.exception("URL Validation no longer works -- Code fix required")
        return False
