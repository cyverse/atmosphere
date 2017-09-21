from django.db import models
from django.db.models import Q
from core.models.user import AtmosphereUser
# from threepio import logger


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
    allow_access = models.BooleanField(default=True)

    class Meta:
        db_table = 'pattern_match'
        app_label = 'core'

    def __unicode__(self):
        access_label = "allow access for" if self.allow_access \
            else "deny access for"
        return "%s users with %s:%s" % (access_label, self.type, self.pattern)

    def validate_users(self):
        """
        Use SQL to filter-down the atmo_users affected
        """
        from core.models import AtmosphereUser
        contains = False
        if ',' in self.pattern:
            test_patterns = self.pattern.split(",")
        elif '*' in self.pattern:
            contains = True
            test_patterns = [self.pattern.replace('*', '')]
        else:
            test_patterns = [self.pattern]
        test_term = 'email' if self.type.name == 'Email' else 'username'
        if contains:
            test_term += "__contains"

        queries = []
        for pattern in test_patterns:
            query = Q(**{test_term: pattern})
            if not self.allow_access:
                query = ~query
            queries.append(query)
        return AtmosphereUser.objects.filter(*queries)


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
