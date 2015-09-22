"""
Atmosphere authentication models..
"""
from datetime import timedelta
import hashlib
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from authentication.settings import auth_settings


AUTH_USER_MODEL = getattr(settings, "AUTH_USER_MODEL", 'auth.User')


class Token(models.Model):

    """
    AuthTokens are issued (or reused if existing)
    each time a user asks for a token using CloudAuth
    """
    key = models.CharField(max_length=1024, primary_key=True)
    user = models.ForeignKey(AUTH_USER_MODEL, related_name='auth_token')
    api_server_url = models.CharField(max_length=256)
    remote_ip = models.CharField(max_length=128, null=True, blank=True)
    issuer = models.TextField(null=True, blank=True)
    issuedTime = models.DateTimeField(auto_now_add=True)
    expireTime = models.DateTimeField(null=True, blank=True)

    def get_expired_time(self):
        return self.expireTime.strftime("%b %d, %Y %H:%M:%S")

    def is_expired(self, now_time=None):
        """
        Returns True if token has expired, False if token is valid
        """
        if not now_time:
            now_time = timezone.now()
        return self.expireTime is not None\
            and self.expireTime <= now_time

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
        hashed_val = hashlib.md5(unique).hexdigest()
        return hashed_val

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


def create_token(username, token_key=None, token_expire=None, issuer=None):
    """
    Generate a Token based on current username
    (And token_key, expiration, issuer.. If available)
    """
    User = get_user_model()
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        logger.warn("User %s doesn't exist on the DB. "
                    "Auth Token _NOT_ created" % username)
        return None
    auth_user_token, _ = Token.objects.get_or_create(
        key=token_key, user=user, issuer=issuer, api_server_url=settings.API_SERVER_URL)
    if token_expire:
        auth_user_token.update_expiration(token_expire)
        auth_user_token.save()
    return auth_user_token


def get_or_create_user(username=None, attributes=None):
    """
    Retrieve or create a User matching the username (No password)
    """
    User = get_user_model()
    if not username:
        return None

    # NOTE: REMOVE this when it is no longer true!
    # Force any username lookup to be in lowercase
    username = username.lower()

    try:
        # Look for the username "EXACT MATCH"
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        user = User.objects.create_user(username, "")
    if attributes:
        user.first_name = attributes['firstName']
        user.last_name = attributes['lastName']
        user.email = attributes['email']
    user.save()
    return user


def lookupSessionToken(request):
    """
    Retrieve an existing token from the request session.
    """
    token_key = request.session['token']
    try:
        token = AuthToken.objects.get(user=request.user, key=token_key)
        if token.is_expired():
            return None
        return token
    except:
        return None


def validateToken(username, token_key):
    """
    Verify the token belongs to username, and renew it
    """
    auth_user_token = AuthToken.objects.filter(
        user__username=username, key=token_key)
    if not auth_user_token:
        return None
    auth_user_token = auth_user_token[0]
    auth_user_token.update_expiration()
    auth_user_token.save()
    return auth_user_token


def userCanEmulate(username):
    """
    Django users marked as 'staff' have emulate permission
    Additional checks can be added later..
    """
    User = get_user_model()
    try:
        user = User.objects.get(username=username)
        return user.is_staff
    except User.DoesNotExist:
        return False
