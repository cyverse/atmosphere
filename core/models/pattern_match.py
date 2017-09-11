from django.db import models
from core.models.user import AtmosphereUser
from threepio import logger

class MatchType(models.Model):
    """
    MatchType objects are created by developers,
    they should NOT be added/removed unless there
    are corresponding logic-choices in core code.

    MatchTypes can be added via `./manage.py loaddata pattern_match.json`
    MatchType:
    - Email - allows wildcard matching on Users email:
      Example :
      - Wildcard: *@email.edu matches (user@email.edu, support@email.edu)

    - Username - Username(s) to be allowed.
      Examples:
      - Single user    :  dnademo matches (dnademo)
      - Comma separated: dnademo1,dnademo2 matches (dnademo1, dnademo2)
      - Wildcard match : dnademo* matches (dnademo1, dnademo2, ...)
    """
    name = models.CharField(max_length=128)

    def __unicode__(self):
        return "%s" % (self.name,)


class PatternMatch(models.Model):

    """
    pattern - the actual string to be matched on
    type - logic to use for matching the string
    """
    pattern = models.CharField(max_length=256)
    type = models.ForeignKey(MatchType)
    created_by = models.ForeignKey(AtmosphereUser)

    class Meta:
        db_table = 'pattern_match'
        app_label = 'core'

    def __unicode__(self):
        return "%s: %s" % (self.type, self.pattern)

    def validate(self, atmo_user):
        if self.type.name == 'Email':
            result = _test_user_email(atmo_user, self.pattern)
        elif self.type.name == "Username":
            result = _test_username(atmo_user, self.pattern)
        else:
            raise ValueError("Encountered an unexpected type: %s" % self.type.name)
        return result


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
    email_pattern = email_pattern.lower()
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
    if '*' in username_match:
        result = _simple_match(username, username_match, contains=True)
    elif ',' in username_match:
        user_matches = username_match.split(",")
        result = any([_simple_match(username, match, contains=False) for match in user_matches])
    else:
        result = _simple_match(username, username_match, contains=False)
    logger.info(
        "Username:%s Match On:%s - Result:%s" %
        (username, username_match, result))
    return result


def create_pattern_match(pattern, pattern_type, created_by):
    pattern_type = pattern_type.lower()
    if "email" in pattern_type:
        match_type = MatchType.objects.get(name="Email")
    elif "user" in pattern_type:
        match_type = MatchType.objects.get(name="Username")
    else:
        raise ValueError("Received invalid pattern_type: %s" % pattern_type)
    pattern = PatternMatch(
        pattern=pattern,
        type=match_type)
    pattern.save()
    return pattern
