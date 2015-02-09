from django.db import models


class ApplicationTag(models.Model):
    application = models.ForeignKey('Application')
    tag = models.ForeignKey('Tag')

    class Meta:
        db_table = 'application_tags'
        app_label = 'core'