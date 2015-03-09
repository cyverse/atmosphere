from django.db import models
from core.models.application import Application
from core.models.tag import Tag


class ApplicationTag(models.Model):
    application = models.ForeignKey(Application)
    tag = models.ForeignKey(Tag)

    class Meta:
        db_table = 'application_tags'
