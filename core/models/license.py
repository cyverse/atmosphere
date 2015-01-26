from django.db import models

from core.models.user import AtmosphereUser

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
    allow_imaging = models.BooleanField(default=True)
    created_by = models.ForeignKey(AtmosphereUser)

    def __unicode__(self):
        return "%s - Re-Imaging Allowed:%s " %\
            (self.title, self.allow_imaging)

    class Meta:
        db_table = 'license'
        app_label = 'core'



