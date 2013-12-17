from django.db.models.signals import post_save
from django.db import models

from threepio import logger

from core.ldap import get_uid_number
from core.models.user import AtmosphereUser
from core.models.group import getUsergroup
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
        identity = getDefaultIdentity(self.user.username)
        identity_member = identity.identitymembership_set.all()[0]
        return identity_member.quota

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
    if prof[1] == True:
        logger.debug("Creating User Profile for %s" % instance)

post_save.connect(get_or_create_user_profile, sender=AtmosphereUser)


def getDefaultProvider(username):
    """
    return the Default provider given to the user-group
    """
    profile = UserProfile.objects.get(user__username=username)
    if profile.selected_provider:
        return profile.selected_provider
    else:
        try:
            group = getUsergroup(username)
            profile.selected_provider = group.providers.get(
                location="EUCALYPTUS")
            profile.save()
            logger.debug(
                "profile.selected_provider set to %s " %
                profile.selected_provider)
            return profile.selected_provider
        except IndexError:
            logger.info("No provider found for %s" % username)
            return None
        except Exception, e:
            logger.exception(e)
            return None


def getDefaultIdentity(username, provider=None):
    """
    return the Default identity given to the user-group for provider
    """
    profile = UserProfile.objects.get(user__username=username)
    if profile.selected_identity:
        return profile.selected_identity
    else:
        try:
            group = getUsergroup(username)
            identities = group.identities.all()
            if provider:
                identities = identities.filter(provider=provider)
                return identities[0]
            else:
                default_identity = group.identities.filter(
                    provider__location="EUCALYPTUS")[0]
                profile.selected_identity = default_identity
                profile.save()
                logger.debug(
                    "profile.selected_identity set to %s " %
                    profile.selected_identity)
                return profile.selected_identity
        except Exception, e:
            logger.exception(e)
            return None
