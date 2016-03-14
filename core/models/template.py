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
    link_getting_started = models.CharField(
        max_length=254, null=True, blank=True)
    link_new_provider = models.CharField(max_length=254, null=True, blank=True)
    link_faq = models.CharField(max_length=254, null=True, blank=True)
    email_address = models.EmailField(null=True, blank=True)  # max_length=254
    email_header = models.TextField(null=True, blank=True)
    email_footer = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'email_template'
        app_label = 'core'
