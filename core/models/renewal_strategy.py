from django.db import models

class RenewalStrategy(models.Model):
    """
        Representation of a Renewal Strategy
    """
    name = models.CharField(max_length=32)
    description = models.CharField(max_length=256, default="", blank=True)

    def __unicode__(self):
        return "%s" % (self.name)
