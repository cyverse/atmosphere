from django.db import models
from core.models.user import AtmosphereUser


class MatchType(models.Model):

    """
    MatchType objects are created by developers,
    they should NOT be added/removed unless there
    are corresponding logic-choices in core code.
    """
    name = models.CharField(max_length=128)

    def __unicode__(self):
        return "%s" % (self.name,)


class PatternMatch(models.Model):

    """
    pattern - the actual string to be matched on
    type - How that string is matched
    """
    pattern = models.CharField(max_length=256)
    type = models.ForeignKey(MatchType)
    created_by = models.ForeignKey(AtmosphereUser)

    class Meta:
        db_table = 'pattern_match'
        app_label = 'core'

    def __unicode__(self):
        return "%s: %s" % (self.type, self.pattern)
