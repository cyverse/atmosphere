"""
Template classes for 'dynamic settings'
that are operator specific can be found
here.

IF you find that DB access is 'too slow'
we should move SingletonModel to `django-solo`
which will provide th same functionality
+ caching layer
"""
from django.db import models

from core.models.abstract import SingletonModel


class EmailTemplate(SingletonModel):
    """
    E-mail template model for atmosphere.
    EmailTemplates are used per 'Site/Installation'.
    keys should NOT be added/removed unless there
    are corresponding logic-choices in core code.
    """
    link_getting_started = models.CharField(max_length=254, default=b"https://pods.iplantcollaborative.org/wiki/display/atmman/Using+Instances")
    link_new_provider = models.CharField(max_length=254, default=b"https://pods.iplantcollaborative.org/wiki/display/atmman/Changing+Providers")
    link_faq = models.CharField(max_length=254, default=b'')
    email_address = models.EmailField(max_length=254, default=b'support@iplantcollaborative.org')
    email_header = models.TextField(default=b'')
    email_footer = models.TextField(default=b'iPlant Atmosphere Team')

    class Meta:
        db_table = 'email_template'
        app_label = 'core'
