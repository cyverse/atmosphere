"""
  ExternalLink model for atmosphere.
"""
import uuid

from django.db import models

from core.query import only_current


class ExternalLink(models.Model):

    """
    An External Link is like a 'Bookmark', ExternalLinks are
    completely managed by end-users.
    ExternalLinks can be added or removed from a project.
    NOTE: Using this as the 'model' for DB moving to ID==UUID format.
    """
    # Required
    id = models.UUIDField(primary_key=True, default=uuid.uuid4,
                          unique=True, editable=False)
    title = models.CharField(max_length=256)
    link = models.URLField(max_length=256)
    # Optional/default available
    description = models.TextField(null=True, blank=True)
    # User/Identity that created the external link
    created_by = models.ForeignKey('AtmosphereUser')

    def get_projects(self, user):
        projects = self.projects.filter(
            only_current(),
            owner=user,
        )
        return projects

    def __unicode__(self):
        return "%s - Author: %s" % (self.title, self.created_by)

    class Meta:
        db_table = 'external_link'
        app_label = 'core'
