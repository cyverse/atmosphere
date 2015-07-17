"""
Service Provider model for atmosphere.
"""

from django.db import models
from django.utils import timezone
from core.models.provider import Provider


class NodeController(models.Model):

    """
    NodeControllers are specific to a provider
    They have a dedicated, static IP address and a human readable name
    To use the image manager they must also provide a valid private ssh key
    """
    provider = models.ForeignKey(Provider)
    alias = models.CharField(max_length=256)
    hostname = models.CharField(max_length=256)
    port = models.IntegerField(default=22)
    private_ssh_key = models.TextField()
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)

    def ssh_key_added(self):
        return len(self.private_ssh_key) > 0
    ssh_key_added.boolean = True

    def __unicode__(self):
        return "%s - %s" % (self.alias, self.hostname)

    class Meta:
        db_table = 'node_controller'
        app_label = 'core'
