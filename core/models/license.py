from django.db import models
from uuid import uuid4

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
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    title = models.CharField(max_length=256)
    license_type = models.ForeignKey(LicenseType)
    license_text = models.TextField()
    access_list = models.ManyToManyField(PatternMatch, blank=True)
    created_by = models.ForeignKey(AtmosphereUser)

    def allowed_access(self):
        return self.access_list.all()

    def __unicode__(self):
        return "%s - Access List:%s" %\
            (self.title, self.allowed_access())

    class Meta:
        db_table = 'license'
        app_label = 'core'


class ApplicationVersionLicense(models.Model):
    """
    Represents the M2M table auto-created by 'application_version.licenses'
    """
    image_version = models.ForeignKey("ApplicationVersion",
                                      db_column='applicationversion_id')
    license = models.ForeignKey(License)

    def __unicode__(self):
        return "(ApplicationVersion:%s - License:%s) " %\
            (self.image_version, self.license.title)

    class Meta:
        db_table = 'application_version_licenses'
        app_label = 'core'
        managed = False
