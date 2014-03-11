from django.db.models.signals import post_save
from django.db import models

from threepio import logger

from core.ldap import get_uid_number

from core.models.user import AtmosphereUser, get_default_identity
from core.models.identity import Identity

from hashlib import md5


class UserProfile(models.Model):
    user = models.OneToOneField(AtmosphereUser, primary_key=True)
    #Backend Profile attributes
    send_emails = models.BooleanField(default=True)
    quick_launch = models.BooleanField(default=True)
    vnc_resolution = models.CharField(max_length=255, default='800x600')
    #Frontend profile attributes
    default_size = models.CharField(max_length=255, default='m1.small')
    background = models.CharField(max_length=255, default='default')
    icon_set = models.CharField(max_length=255, default='default')

    def user_quota(self):
        identity = get_default_identity(self.user.username)
        identity_member = identity.identitymembership_set.all()[0]
        return identity_member.get_quota_dict()

    def email_hash(self):
        m = md5()
        m.update(self.user.email)
        return m.hexdigest()

    class Meta:
        db_table = 'user_profile'
        app_label = 'core'


#Connects a user profile to created accounts
def get_or_create_user_profile(sender, instance, created, **kwargs):
    prof = UserProfile.objects.get_or_create(user=instance)
    if prof[1] is True:
        logger.debug("Creating User Profile for %s" % instance)


post_save.connect(get_or_create_user_profile, sender=AtmosphereUser)
