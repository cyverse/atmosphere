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
    # One week
    threshold = models.IntegerField(null=True,
                                    blank=True,
                                    default=7*24*60)  # In Minutes
    # Over One year
    delta = models.IntegerField(null=True,
                                blank=True,
                                default=365*24*60)  # In Minutes

    def __unicode__(self):
        return "Threshold: %s minutes over Delta: %s minutes" %\
            (self.threshold, self.delta)

    @classmethod
    def default_allocation(self, provider=None):
        """
        TODO: Refactor so that a provider can define NEW default allocations,
        rather than hard-coded
        """
        return Allocation.objects.get_or_create(
            **Allocation.default_dict())[0]

    @classmethod
    def default_dict(self):
        return {
            'threshold': self._meta.get_field('threshold').default,
            'delta': self._meta.get_field('delta').default
        }

    class Meta:
        db_table = 'allocation'
        app_label = 'core'
