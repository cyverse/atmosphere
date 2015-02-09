from django.db import models


class InstanceTag(models.Model):
    instance = models.ForeignKey('Instance')
    tag = models.ForeignKey('Tag')

    class Meta:
        db_table = 'instance_tags'
        app_label = 'core'