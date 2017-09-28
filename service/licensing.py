"""
   Logic related to License, PatternMatch, etc. for atmosphere.
"""

from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

from core.models.license import License, LicenseType
from core.models.pattern_match import PatternMatch, MatchType
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
    except ValidationError as e:
        return False
    except:
        logger.exception("URL Validation no longer works -- Code fix required")
        return False
