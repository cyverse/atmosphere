from django.db import models


class InstanceAction(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField()

    class Meta:
        db_table = 'instance_action'
        app_label = 'core'