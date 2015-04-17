from django.db import models

from core.models.user import AtmosphereUser
from core.models.match import PatternMatch

class LicenseType(models.Model):
    """
    LicenseType objects are created by developers,
    they should NOT be added/removed unless there
    are corresponding logic-choices in core code.
    """
    name = models.CharField(max_length=128)
    description = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'license_type'
        app_label = 'core'

    def __unicode__(self):
        return self.name

class License(models.Model):
    """
    """
    title = models.CharField(max_length=256)
    license_type = models.ForeignKey(LicenseType)
    license_text = models.TextField()
    access_list = models.ManyToManyField(PatternMatch, blank=True)
    created_by = models.ForeignKey(AtmosphereUser)

    def allowed_access(self):
        return self.access_list.all()

    def __unicode__(self):
        return "%s - Re-Imaging Allowed:%s %s" %\
            (self.title, self.allow_imaging, self.allowed_access())

    class Meta:
        db_table = 'license'
        app_label = 'core'
