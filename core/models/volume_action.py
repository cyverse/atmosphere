from django.db import models


class VolumeAction(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField()

    class Meta:
        db_table = 'volume_action'
        app_label = 'core'