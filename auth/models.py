"""
Atmosphere authentication models..
"""

#Python libraries
import uuid
import hashlib
from datetime import datetime, timedelta
from django.utils import timezone
#Django libraries
from django.db import models
from django.contrib.auth.models import User

class Token(models.Model):
    """
    AuthTokens are issued (or reused if existing) each time a user validates with CloudAuth
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
        return self.expireTime != None and self.expireTime <= timezone.now()

    def update_expiration(self):
        """
        Updates expiration by pre-determined amount.. Does not call save.
        """
        self.expireTime = datetime.now() + timedelta(hours=2)

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super(Token, self).save(*args, **kwargs)

    def generate_key(self):
        unique = str(uuid.uuid4())
        return hashlib.md5(unique).hexdigest()

    def __unicode__(self):
        return "%s" % (self.key)

#New 03/29/12
class UserProxy(models.Model):
    """
      The UserProxy model is used to Map username+proxyIOU to the proxyIOU+proxyTicket request from CAS
    """
    username = models.CharField(max_length=128, blank=True, null=True)
    proxyIOU = models.CharField(max_length=40)
    proxyTicket = models.CharField(max_length=70)
    expiresOn = models.DateTimeField(blank=True, null=True)

    def __unicode__(self):
        return "%s CAS_Proxy" % self.username
