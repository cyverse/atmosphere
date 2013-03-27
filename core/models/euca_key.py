"""
  Euca_Key model for atmosphere. From Atmosphere API v1.
"""

from django.db import models


class Euca_Key(models.Model):
    """
    Euca keys are a type of Credential:
    ec2_access_key, ec2_secret_key, ec2_url, s3_url
    """
    username = models.CharField(max_length=256)
    ec2_access_key = models.TextField()
    ec2_secret_key = models.TextField()
    ec2_url = models.TextField()
    s3_url = models.TextField()

    def __unicode__(self):
        return self.username

    class Meta:
        db_table = "service_euca_key"
        app_label = "service_old"
