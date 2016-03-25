"""
Track Atmosphere transactions across our system.
"""
from django.db import models
from uuid import uuid1
from django.utils import timezone


class T(models.Model):

    """
    Track Atmosphere transactions across our system.
    """

    # A unique UUID (V)alue for the transaction.
    V = models.CharField(max_length=36)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True)

    def __unicode__(self):
        return "%s: %s - %s" %\
            (self.V, self.start_date, self.end_date)

    @classmethod
    def create(cls):
        return cls(V=uuid1())

    @classmethod
    def get(cls):
        t = T.create()
        with transaction.atomic():
            t.save()
        return t

    class Meta:
        db_table = "transaction"
        app_label = "core"
