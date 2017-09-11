from django.db import models
from core.models.application import Application
from core.models.match import PatternMatch


class ApplicationPatternMatch(models.Model):
    """
    This model allows us to directly modify the 'join table'
    implicity created by Django when we set 'Application.tags'
    """
    application = models.ForeignKey(Application)
    match = models.ForeignKey(PatternMatch)

    def __unicode__(self):
        return "%s: %s - %s" %\
            (self.id, self.application, self.match)

    class Meta:
        db_table = 'application_future_access_list'
        managed = False
