"""
Atmosphere authentication models..
"""

import uuid
import hashlib
from datetime import timedelta

from django.utils import timezone
from django.db import models

from core.models import AtmosphereUser as User


class Token(models.Model):
    """
    AuthTokens are issued (or reused if existing)
    each time a user asks for a token using CloudAuth
    """
    key = models.CharField(max_length=64, primary_key=True)
    user = models.ForeignKey(User, related_name='auth_token')
    api_server_url = models.CharField(max_length=256)
    remote_ip = models.CharField(max_length=128, null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    issuedTime = models.DateTimeField(auto_now_add=True)
    expireTime = models.DateTimeField(null=True, blank=True)

    def is_expired(self):
        """
        Returns True if token has expired, False if token is valid
        """
        return self.expireTime is not None\
            and self.expireTime <= timezone.now()

    def update_expiration(self, token_expiration=None):
        """
        Updates expiration by pre-determined amount.. Does not call save.
        """
        if not token_expiration:
            self.expireTime = timezone.now() + timedelta(hours=2)
        else:
            self.expireTime = token_expiration

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super(Token, self).save(*args, **kwargs)

    def generate_key(self):
        unique = str(uuid.uuid4())
        return hashlib.md5(unique).hexdigest()

    def __unicode__(self):
        return "%s" % (self.key)

    class Meta:
        db_table = "auth_token"
        app_label = "authentication"


class UserProxy(models.Model):
    """
      The UserProxy model
      Maps username+proxyIOU (Returned on serviceValidate+proxy)
      to proxyIOU+proxyTicket(sent to the proxy URL)
    """
    username = models.CharField(max_length=128, blank=True, null=True)
    proxyIOU = models.CharField(max_length=128)
    proxyTicket = models.CharField(max_length=128)
    expiresOn = models.DateTimeField(blank=True, null=True)

    def __unicode__(self):
        return "%s CAS_Proxy" % self.username

    class Meta:
        db_table = "auth_userproxy"
        app_label = "authentication"
        verbose_name_plural = 'user proxies'
