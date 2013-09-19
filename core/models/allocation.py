"""
Service Time Allocation model for atmosphere.
"""

from django.db import models


class Allocation(models.Model):
    """
    Allocation limits the amount of time resources that can be used for
    a User/Group. Allocations are set at the Identity Level
    in IdentityMembership.
    """
    threshold = models.IntegerField(null=True,
                                    blank=True,
                                    default=10080)  # In Minutes
    delta = models.IntegerField(null=True,
                                blank=True,
                                default=20160)  # In Minutes

    def __unicode__(self):
        return "Threshold: %s minutes over Delta: %s minutes" %
        (self.threshold, self.delta)

    @classmethod
    def defaults(self):
        return {
            'threshold': self._meta.get_field('threshold').default,
            'delta': self._meta.get_field('delta').default
        }

    class Meta:
        db_table = 'allocation'
        app_label = 'core'
