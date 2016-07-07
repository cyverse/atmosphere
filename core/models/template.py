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
    email_address = models.EmailField(max_length=254, default=b'support@cyverse.org')
    email_header = models.TextField(default=b'')
    email_footer = models.TextField(default=b'CyVerse Atmosphere Team')
    links = models.ManyToManyField("HelpLink", related_name='email_templates')

    def get_link(self, link_key):
        try:
            return self.links.get(link_key=link_key)
        except models.ObjectDoesNotExist:
            return None

    class Meta:
        db_table = 'email_template'
        app_label = 'core'

class HelpLink(models.Model):
    """
    HelpLinks are used in Atmosphere and the Tropo UI (via API call)
    HelpLinks are used per 'Site/Installation'.
    New HelpLinks should *NOT* be added/removed unless there
    are corresponding logic-choices in core code.
    """
    link_key = models.CharField(max_length=256, unique=True, editable=False)
    topic = models.CharField(max_length=256)
    context = models.TextField(default='', null=True, blank=True)
    href = models.TextField()

    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    def delete(self, *args, **kwargs):
        """
        Block the outright deletion of HelpLinks
        """
        pass

    def __unicode__(self):
        return "%s(%s) => %s" % (self.topic, self.link_key, self.href)
